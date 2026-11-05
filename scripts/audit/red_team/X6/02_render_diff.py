"""Render all reports + site from committed tables into scratch; diff vs reports/*.md and website/index.html.
Uses render_all(out_dir=scratch) and site.render_template (no repo writes)."""
import pathlib, difflib
from nhtsa_stats.reporting import render, site
S = pathlib.Path("/tmp/claude-0/-home-user-nhtsa-stats-US/1c16118e-b425-5b4c-9882-66195720c5ff/scratchpad/red_team/work/X6/render"); S.mkdir(exist_ok=True)
R = pathlib.Path("reports")
for p in render.render_all(out_dir=S):
    a = (R / p.name).read_text(); b = p.read_text()
    print(p.name, "IDENTICAL" if a == b else "DIFFERS")
    if a != b:
        for l in list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0))[:12]: print("   ", l[:200])
render._table.cache_clear()
page = site.render_template(pathlib.Path("website/templates/index.html").read_text())
site.validate(page)
(S / "index.html").write_text(page)
a = pathlib.Path("website/index.html").read_text()
print("site", "IDENTICAL" if a == page else "DIFFERS", len(a), len(page))
if a != page:
    for l in list(difflib.unified_diff(a.splitlines(), page.splitlines(), lineterm="", n=0))[:20]: print("   ", l[:200])
