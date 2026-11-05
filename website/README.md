# Road Deaths in America: public website

A single static page. Every number and chart is rendered at build time from the committed tables in `outputs/tables/`, so nothing on the page is typed by hand.

## Pipeline

1. `website/templates/index.html` holds the prose. Numbers are placeholders of the report grammar (`{{deaths/segments|segment=all|deaths|,.0f}}`, see `src/nhtsa_stats/reporting/render.py`). Directives: `{{chart:<id>}}`, `{{statestable}}`, `{{asset:css}}`, `{{asset:js}}`.
2. `uv run nhtsa analyze site` (`src/nhtsa_stats/reporting/site.py`) renders the template into `website/index.html`, one self-contained file with CSS and JS inlined. It fails on an unresolved placeholder or a NaN-like value. Edit the template, `assets/site.css` or `assets/site.js`, never `index.html`.
3. `python3 website/tools/sync_public_data.py` copies exactly 19 CSV files into `website/data/tables/`, keeping their `outputs/tables/` paths: every `outputs/tables/deaths/*.csv` (13 files) and six cited tables listed in the tool's `CITED` (`severity/fatal_speeding_type`, `vulnerable/pedestrian_killed_contrasts`, `vulnerable/fars_pedestrian_deaths_by_striking_vehicle`, `person/lpv_killed_crude_vs_adjusted`, `matched/belt_effect`, `matched/double_pair_comparison`). Nothing else is copied (no JSON sidecars). Every one of these files is linked from the page and every link on the page points to one (`tests/test_site.py` checks both directions). It deletes snapshots no longer listed; `--check` fails on a missing, stale or orphan file.

Charts are HTML and CSS bars, plus SVG for line charts, each with a "Show the data" table. `assets/site.js` is optional enhancement: tooltips, line-chart crosshair, states table sorting and filtering, nav highlight.

## Checks

```bash
uv run pytest -q tests/test_site.py   # page equals a fresh render; no hand-typed numbers; chart builders and fixed-scale guards; CSV links match the sync tool
node --check website/assets/site.js
node --test website/tests/site.test.mjs
python3 website/tools/sync_public_data.py --check
```

Preview: `python3 -m http.server 8000 --directory website`.
