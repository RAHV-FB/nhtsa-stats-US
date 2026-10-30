# Road Evidence — public research website

Responsive, static front end for the **FARS & CRSS 2016–2024** US road-safety study. It complements, and does not replace, the nine-page Streamlit research app.

## Structure

index.html is one page of plain, sourced data stories, in this order:

1. Intro and four key figures.
2. Six stories, each with a short text, a chart drawn at runtime from a bundled CSV, a caveat and a source line: deaths by year, who died, pedestrians (striking vehicle, speed and darkness, vehicle type), time of day, age, rural roads.
3. Limits of the data, linking to the limitations report.
4. Explore the tables: the data explorer (four tables, CI whiskers, searchable) with the underlying rows.
5. Full reports: the library that renders eleven generated Markdown reports and documents in the browser.

assets/site.js has no dependencies. It holds the SVG line chart, the horizontal bars (with optional CI whiskers), the grouped bars, the data explorer, the CSV parser and the Markdown renderer. Every chart has role="img" with an aria-label that summarises its data, and a "Show the data" table with the rows.

Public data lives in website/data/ and is copied by website/tools/sync_public_data.py. Do not edit it by hand. The page uses these tables: descriptive/fars_annual, descriptive/frequency_vs_severity, trends/fars_changes, vulnerable (striking vehicle, killed contrasts, light truck by speed), person/lpv_killed_crude_vs_adjusted, stages (death timing, EMS availability), severity/fatal_crude_vs_adjusted and contributions/ranking, plus findings.json and the reports.

Claims test: website/tests/site.test.mjs binds every number written in prose in index.html or site.js to its bundled CSV value through a formatter, counts exact occurrences with digit boundaries, and fails on any other number in the page text. Sums, differences and shares (for example 69% of the increase) are derived from the CSVs in the test.

## Run locally

From the repository root:

1. Run: python website/tools/sync_public_data.py
2. Run: node --test website/tests/site.test.mjs
3. Run: python website/tools/sync_public_data.py --check
4. Run: python -m http.server 8000 --directory website
5. Visit: http://localhost:8000

The published site needs only a static host, not Streamlit, server-side Python, raw archives or Git LFS.

## Deployment

.github/workflows/public-site.yml validates the website and source snapshots. On a push to main, it attempts to deploy the website directory with GitHub Pages.

The site is live at https://rahv-fb.github.io/nhtsa-stats-US/ (Repository Settings → Pages → Source: GitHub Actions). The verify job also runs on pull requests that touch website/, reports/, docs/ or outputs/tables/, so a stale snapshot or a number in the page text that no longer matches its table fails CI before merge.

## Scientific provenance

The canonical source of every displayed data value is the project's generated source reports and output tables. The public data copies are mapped by website/tools/sync_public_data.py and checked by CI. Do not manually change website/data.

When analysis results change, regenerate reports using the established research pipeline, synchronize the public snapshots and review the explanatory text for alignment. Never turn adjusted associations into causal claims.

The nine-page technical interface remains runnable through: uv run streamlit run app/streamlit_app.py

The research cannot measure risk per journey or kilometre, intervention effects, selective drug-testing biases away, or individual causal shares of deaths.
