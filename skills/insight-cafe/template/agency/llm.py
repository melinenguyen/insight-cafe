"""
Which AI writes the café's reports. Put one key in agency/.env (or in the repo's secrets on GitHub):

    GEMINI_API_KEY=…       Google's Gemini on its free tier (aistudio.google.com/apikey). Free, no card.
    OPENROUTER_API_KEY=…   free open-source models through OpenRouter (openrouter.ai/keys). Free, no card.
    ANTHROPIC_API_KEY=…    Claude, about $1 a report. The sharpest writing.
    AGENCY_AI=ollama       an open-source model on your own computer (ollama.com). Free, nothing leaves it.

With more than one key, AGENCY_AI picks (claude, gemini, openrouter, ollama or custom). AGENCY_MODEL swaps the
model, or a comma-separated list of models to try in order. Any other OpenAI-compatible service works as
AGENCY_AI=custom with LLM_BASE_URL, LLM_API_KEY and LLM_MODEL.

Free tiers have daily limits and may use what you send to improve their models; the café only sends public
signals and your brand profile. Every answer is checked against the desk's JSON shape and repaired or asked
for again, because free models are looser with structure than Claude.
"""

from __future__ import annotations

import json
import logging
import re
import time

import requests

from . import config

log = logging.getLogger("agency.llm")

PROVIDERS = {
    "claude": {"label": "Claude", "key": "ANTHROPIC_API_KEY", "models": [config.MODEL]},
    "gemini": {"label": "Gemini (free tier)", "key": "GEMINI_API_KEY",
               "base": "https://generativelanguage.googleapis.com/v1beta/openai",
               # the newest Flash first; Flash-Lite has a far larger free daily allowance
               "models": ["gemini-flash-latest", "gemini-flash-lite-latest"]},
    "openrouter": {"label": "open-source models via OpenRouter (free)", "key": "OPENROUTER_API_KEY",
                   "base": "https://openrouter.ai/api/v1",
                   # NVIDIA's open-weight Nemotron, then whichever free model OpenRouter has that can write JSON
                   "models": ["nvidia/nemotron-3-super-120b-a12b:free", "openrouter/free"]},
    "ollama": {"label": "Ollama on this computer", "key": "", "base": "http://localhost:11434", "models": ["qwen3:8b"]},
    "custom": {"label": "your own AI", "key": "LLM_API_KEY", "base": "", "models": []},
}
PRICE_USD = {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 5.0}  # Claude Opus 5.5 per 1M tokens
MAX_OUT = 16000


class KeyRefused(RuntimeError):
    """The provider said no to the key itself: no point trying another model."""


def pick() -> str:
    """The provider: AGENCY_AI if set, otherwise the first one with a key."""
    name = config.env("AGENCY_AI").lower()
    if name:
        if name not in PROVIDERS:
            raise SystemExit(f"✕ AGENCY_AI={name} isn't one I know. Use one of: {', '.join(PROVIDERS)}.")
        return name
    for name in ("claude", "gemini", "openrouter"):
        if config.env(PROVIDERS[name]["key"]) or (name == "claude" and config.env("ANTHROPIC_AUTH_TOKEN")):
            return name
    return "custom" if config.env("LLM_BASE_URL") else ""


def missing_key_help() -> str:
    return ("✕ No AI key yet. Pick one and add it to agency/.env, then run again:\n"
            "  GEMINI_API_KEY=…      free: https://aistudio.google.com/apikey\n"
            "  OPENROUTER_API_KEY=…  free open-source models: https://openrouter.ai/keys\n"
            "  ANTHROPIC_API_KEY=…   Claude, about $1 a report: https://console.anthropic.com/settings/keys")


class Client:
    def __init__(self, provider: str | None = None):
        self.name = provider or pick()
        if not self.name:
            raise SystemExit(missing_key_help())
        p = PROVIDERS[self.name]
        self.label = p["label"]
        self.key = config.env(p["key"]) if p["key"] else ""
        self.base = p["base"]
        if self.name == "custom":
            self.base = config.env("LLM_BASE_URL")
        elif self.name == "ollama" and config.env("OLLAMA_HOST"):
            host = config.env("OLLAMA_HOST")
            self.base = host if host.startswith("http") else "http://" + host
        self.base = self.base.rstrip("/")
        chosen = config.env("AGENCY_MODEL") or (config.env("LLM_MODEL") if self.name == "custom" else "")
        self.models = [m.strip() for m in chosen.split(",") if m.strip()] or list(p["models"])
        if not self.models:
            raise SystemExit("✕ AGENCY_AI=custom needs LLM_MODEL (and LLM_BASE_URL, LLM_API_KEY).")
        self.free = self.name != "claude"
        # a laptop answers one desk at a time; a cloud service takes the three side desks at once
        self.parallel = 1 if self.name == "ollama" else 3
        self._anthropic = None
        self._dead: set[str] = set()   # models that ran out of free requests today
        if self.name == "claude":
            import anthropic
            # long structured outputs with thinking can run past the SDK's 10-minute default
            self._anthropic = anthropic.Anthropic(api_key=self.key or None, max_retries=2, timeout=1800.0)

    def describe(self) -> str:
        return f"{self.label} ({self.models[0]})"

    def ask(self, system: str, user: str, schema: dict, effort: str) -> tuple[dict, dict]:
        """One desk's answer as a dict shaped like `schema`, and what it used."""
        if self._anthropic:
            return self._claude(system, user, schema, effort)
        errors = []
        for model in [m for m in self.models if m not in self._dead] or self.models[-1:]:
            try:
                return self._open(model, system, user, schema, effort)
            except KeyRefused:
                raise
            except Exception as e:  # noqa: BLE001 — try the next model, say what each one said
                log.warning("%s · %s: %s", self.name, model, str(e)[:300])
                errors.append(f"{model}: {str(e)[:160]}")
        raise RuntimeError(f"{self.label} couldn't answer — " + " | ".join(errors))

    # -- Claude -------------------------------------------------------------
    def _claude(self, system: str, user: str, schema: dict, effort: str) -> tuple[dict, dict]:
        with self._anthropic.beta.messages.stream(
            model=self.models[0],
            max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"],
            # the system prompt is identical across the desks, so later calls can read it from cache
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            extra_body={"fallbacks": "default"},
        ) as stream:
            msg = stream.get_final_message()
        if msg.stop_reason == "refusal":
            raise RuntimeError(f"model declined: {getattr(msg, 'stop_details', None)}")
        if msg.stop_reason == "max_tokens":
            raise RuntimeError("output hit max_tokens — the JSON is incomplete")
        u = msg.usage
        cr, cw = getattr(u, "cache_read_input_tokens", 0) or 0, getattr(u, "cache_creation_input_tokens", 0) or 0
        usd = (u.input_tokens * PRICE_USD["input"] + u.output_tokens * PRICE_USD["output"]
               + cr * PRICE_USD["cache_read"] + cw * PRICE_USD["cache_write"]) / 1e6
        usage = {"provider": self.name, "model": msg.model, "effort": effort, "input": u.input_tokens,
                 "output": u.output_tokens, "cache_read": cr, "cache_write": cw, "usd": round(usd, 3)}
        return json.loads(next(b.text for b in msg.content if b.type == "text")), usage

    # -- Gemini, OpenRouter, Ollama, custom -----------------------------------
    def _open(self, model: str, system: str, user: str, schema: dict, effort: str) -> tuple[dict, dict]:
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user + "\n\n" + schema_note(schema)}]
        formats = ["json_schema", "json_object", "none"]
        used = {"input": 0, "output": 0}
        tries = 0
        while True:
            fmt = formats[0]
            try:
                text, finish, u = self._post(model, messages, schema, fmt)
            except FormatRejected:
                formats.pop(0)
                log.info("%s · %s: no %s here, asking for plain JSON", self.name, model, fmt)
                if not formats:
                    raise
                continue
            used["input"] += u.get("prompt_tokens", 0) or 0
            used["output"] += u.get("completion_tokens", 0) or 0
            tries += 1
            try:
                if finish == "length":
                    raise BadAnswer("the answer was cut off before the JSON ended")
                out, fixes = conform(parse_json(text), schema)
                share = fixes / max(1, leaves(out))
                if share > (0.6 if tries >= 2 else 0.3):  # a few gaps are fine; a mostly empty answer isn't
                    raise BadAnswer(f"{fixes} of {leaves(out)} fields were missing or the wrong type")
                if fixes:
                    log.info("%s · %s: repaired %d fields", self.name, model, fixes)
                return out, {"provider": self.name, "model": model, "effort": effort, **used,
                             "cache_read": 0, "cache_write": 0, "usd": 0.0, "repaired": fixes}
            except (BadAnswer, ValueError) as e:
                if tries >= 2:
                    raise RuntimeError(f"no usable JSON after {tries} tries: {e}") from e
                log.info("%s · %s: %s — asking again", self.name, model, e)
                messages = messages[:2] + [
                    {"role": "assistant", "content": (text or "")[:6000]},
                    {"role": "user", "content": f"That answer can't be used: {e}. Reply again with ONE complete JSON "
                                                "object that matches the schema exactly, every key present, nothing "
                                                "before or after it. Keep every text field short."}]

    def _post(self, model: str, messages: list[dict], schema: dict, fmt: str) -> tuple[str, str, dict]:
        """One request, waiting out short rate limits. Returns (text, finish reason, token usage)."""
        if self.name == "ollama":  # Ollama's own API: lets us raise its small default context window
            url = f"{self.base}/api/chat"
            body = {"model": model, "messages": messages, "stream": False,
                    "options": {"num_ctx": 32768, "num_predict": MAX_OUT}}
            if fmt != "none":
                body["format"] = schema if fmt == "json_schema" else "json"
        else:
            url = f"{self.base}/chat/completions"
            body = {"model": model, "messages": messages, "max_tokens": MAX_OUT}
            if fmt == "json_schema":
                body["response_format"] = {"type": "json_schema",
                                           "json_schema": {"name": "answer", "strict": True, "schema": schema}}
            elif fmt == "json_object":
                body["response_format"] = {"type": "json_object"}
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        if self.name == "openrouter":
            headers.update({"HTTP-Referer": "https://github.com/melinenguyen/insight-cafe", "X-Title": "The Insight Cafe"})
        for attempt in range(4):
            try:
                r = requests.post(url, json=body, headers=headers, timeout=(20, 1200 if self.name == "ollama" else 600))
            except requests.RequestException as e:
                if attempt == 3:
                    raise RuntimeError(f"couldn't reach {self.base}: {e}") from e
                time.sleep(10)
                continue
            if r.status_code == 200:
                try:
                    d = r.json()
                except ValueError:
                    raise RuntimeError(f"{self.base} answered, but not with JSON: {r.text[:120]!r}. Check the address.")
                if self.name == "ollama":
                    return (d.get("message") or {}).get("content", ""), ("length" if d.get("done_reason") == "length"
                                                                         else "stop"), \
                        {"prompt_tokens": d.get("prompt_eval_count", 0), "completion_tokens": d.get("eval_count", 0)}
                if d.get("error"):
                    raise RuntimeError(str(d["error"])[:300])
                ch = (d.get("choices") or [{}])[0]
                return (ch.get("message") or {}).get("content") or "", ch.get("finish_reason") or "", d.get("usage") or {}
            said = r.text[:400]
            if (r.status_code in (401, 403) and "quota" not in said.lower()) or \
                    re.search(r"valid API key|API key not valid|API_KEY_INVALID|invalid Authorization|No auth credentials", said):
                raise KeyRefused(f"{self.label} refused the key (HTTP {r.status_code}). Check {PROVIDERS[self.name]['key']}.")
            if r.status_code == 429:
                wait = _retry_after(r)
                daily = re.search(r"per ?day|PerDay|daily|free-models-per-day", said, re.I)
                if daily or wait > 90 or attempt == 3:
                    self._dead.add(model)
                    raise RuntimeError(f"out of free requests for now (HTTP 429): {said[:160]}")
                log.info("%s · %s: rate limited, waiting %ss", self.name, model, wait)
                time.sleep(wait)
                continue
            if r.status_code == 400 and fmt != "none" and re.search(r"response_format|json_schema|schema|format|"
                                                                     r"structured|json", said, re.I):
                raise FormatRejected(said)
            if r.status_code >= 500 and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {r.status_code}: {said}")
        raise RuntimeError("no answer")


class FormatRejected(RuntimeError):
    pass


class BadAnswer(ValueError):
    pass


def _retry_after(r) -> int:
    h = r.headers.get("Retry-After") or r.headers.get("retry-after")
    if h and h.strip().isdigit():
        return int(h)
    m = re.search(r"retry (?:in|after)\D{0,5}(\d+(?:\.\d+)?)\s*s", r.text, re.I) or re.search(r'"retryDelay":\s*"(\d+)', r.text)
    return int(float(m.group(1))) + 1 if m else 20


# ---------------------------------------------------------------------------
# Getting a clean dict out of a free model's answer
# ---------------------------------------------------------------------------
def schema_note(schema: dict) -> str:
    return ("Reply with ONE JSON object and nothing else: no markdown, no comments, no text before or after it. "
            "Every key in the schema must be present (use \"\" or [] when there is nothing to say), and enum fields "
            "must use one of the listed values exactly. JSON schema:\n" + json.dumps(schema, separators=(",", ":")))


def parse_json(text: str) -> dict:
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if fence:
        t = fence.group(1)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end <= start:
        raise BadAnswer("there was no JSON object in the answer")
    t = t[start:end + 1]
    try:
        out = json.loads(t)
    except json.JSONDecodeError:
        try:  # the usual slips: trailing commas, smart quotes around keys
            out = json.loads(re.sub(r",\s*([}\]])", r"\1", t).replace("“", '"').replace("”", '"'))
        except json.JSONDecodeError as e:
            raise BadAnswer(f"the JSON didn't parse ({e.msg} at character {e.pos})") from e
    if not isinstance(out, dict):
        raise BadAnswer("the answer was JSON but not an object")
    return out


def _default(schema: dict):
    if "enum" in schema:
        return _safe_enum(schema["enum"])
    return {"object": lambda: conform({}, schema)[0], "array": list, "integer": lambda: 0,
            "number": lambda: 0, "boolean": lambda: False}.get(schema.get("type"), str)()


def _safe_enum(values: list[str]) -> str:
    """When a model leaves an enum out, the cautious choice: Watch over Act today, Nobody yet over a name."""
    for v in ("Watch", "watch", "Nobody yet", "None", "Awareness", "static"):
        if v in values:
            return v
    return values[0]


def leaves(value) -> int:
    """How many fields an answer has, counting every string, number and empty list."""
    if isinstance(value, dict):
        return sum(leaves(v) for v in value.values()) or 1
    if isinstance(value, list):
        return sum(leaves(v) for v in value) or 1
    return 1


def conform(value, schema: dict) -> tuple[object, int]:
    """Shape `value` like `schema`: fill what's missing, drop what isn't asked for, coerce types.
    Returns (value, how many fixes it took); the caller asks again when that's too many."""
    t, fixes = schema.get("type"), 0
    if t == "object":
        if not isinstance(value, dict):
            value, fixes = {}, 1
        out = {}
        for k, sub in schema.get("properties", {}).items():
            if k in value and value[k] is not None:
                out[k], f = conform(value[k], sub)
                fixes += f
            else:
                out[k], fixes = _default(sub), fixes + 1
        return out, fixes
    if t == "array":
        if isinstance(value, (str, dict)) and value:
            value, fixes = [value], 1
        if not isinstance(value, list):
            return [], 1
        items, out = schema.get("items", {}), []
        for v in value:
            if v is None:
                continue
            c, f = conform(v, items)
            out.append(c)
            fixes += f
        return out, fixes
    if t == "integer" or t == "number":
        try:
            n = float(re.sub(r"[^\d.\-]", "", value) if isinstance(value, str) else value)
            return (int(round(n)) if t == "integer" else n), 0
        except (TypeError, ValueError):
            return 0, 1
    if t == "boolean":
        return (value if isinstance(value, bool) else str(value).lower() in ("true", "yes", "1")), 0
    # strings, and enums of strings
    if isinstance(value, list):
        value, fixes = "; ".join(str(v) for v in value), 1
    elif not isinstance(value, str):
        value, fixes = str(value), 1
    value = value.strip()
    if "enum" in schema and value not in schema["enum"]:
        low = {e.lower(): e for e in schema["enum"]}
        hit = low.get(value.lower()) or next((e for e in schema["enum"] if e.lower() in value.lower()), None)
        return (hit, fixes) if hit else (_safe_enum(schema["enum"]), fixes + 1)
    return value, fixes
