"""Run the suite and render its real output as an image for the gallery.

Only the lines that name a machine (rootdir, cachedir, the interpreter path) are
dropped, so no local path shows up in a public screenshot.
"""

import html
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = ("rootdir:", "cachedir:", "platform ", "plugins:", "collecting ")

result = subprocess.run(
    [str(ROOT / ".venv/bin/python"), "-m", "pytest", "tests", "-v", "--no-header", "-p", "no:cacheprovider"],
    cwd=ROOT,
    capture_output=True,
    text=True,
)
lines = [l.rstrip() for l in result.stdout.splitlines() if l.strip() and not l.startswith(SKIP)]
lines = [re.sub(r"=+", lambda m: "=" * min(len(m.group(0)), 20), l) for l in lines]

rows = []
for line in lines:
    klass = "pass" if line.endswith("]") and "PASSED" in line else "plain"
    if "passed" in line and "=" in line:
        klass = "summary"
    rows.append(f'<div class="{klass}">{html.escape(line)}</div>')

(ROOT / "scripts/tests.html").write_text(
    """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..700&family=Red+Hat+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
 body{margin:0;background:#F4F5F2;font-family:"Red Hat Mono",monospace}
 .card{width:1000px;margin:32px;background:#fff;border:1px solid #DCDED8;padding:32px 36px}
 h3{font-family:"Archivo",sans-serif;font-variation-settings:"wght" 700;font-size:20px;margin:0 0 20px;color:#0F1B2D}
 div.plain,div.pass,div.summary{font-size:14px;line-height:1.75;color:#4A5665;white-space:pre}
 div.pass{color:#0F1B2D}
 div.summary{color:#14315C;font-weight:500;margin-top:12px;border-top:1px solid #EAEBE6;padding-top:12px}
</style></head><body><div class="card"><h3>pytest</h3>"""
    + "".join(rows)
    + "</div></body></html>",
    encoding="utf-8",
)
print(result.returncode, len(rows))
