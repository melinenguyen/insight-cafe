"""Embed profiles/example-us-skincare.json into dashboard/index.html (the 'Load example' data). Re-runnable."""
import json, re, sys
from pathlib import Path
SKILL = Path(__file__).resolve().parent.parent
html_p = SKILL / "dashboard" / "index.html"
ex = json.loads((SKILL / "profiles" / "example-us-skincare.json").read_text(encoding="utf-8"))
blob = json.dumps(ex, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
html = html_p.read_text(encoding="utf-8")
pat = re.compile(r'(<script type="application/json" id="example-profile">)(.*?)(</script>)', re.S)
assert pat.search(html), "example script tag not found"
html = pat.sub(lambda m: m.group(1) + blob + m.group(3), html, count=1)
html_p.write_text(html, encoding="utf-8")
print("embedded", len(blob), "bytes")
