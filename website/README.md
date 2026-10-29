# Road Evidence — public research website

Responsive, static front end for the **FARS & CRSS 2016–2024** US road-safety study. It complements, and does not replace, the nine-page Streamlit research app.

## Included

- Editorial landing page with provenance and uncertainty.
- Searchable and filterable set of all ten Phase 1 findings (confidence intervals, denominators, robustness and limitations).
- Interactive charts for over-representation, adjusted severity, factor rankings and annual fatalities, with underlying table access.
- Analysis of overlapping counts for speed, BAC, drugs and unbelted occupants.
- Speeding, alcohol, drugs and seat-belt research explainers.
- Hypothetical policy break-even calculator computed from the committed threshold baseline (not an assumed intervention effect).
- Provenance test: every statistic written into index.html or site.js is checked against its bundled table (website/tests/site.test.mjs).
- Reader for eleven complete generated reports and technical documents.
- Responsive styles, semantic landmarks, keyboard controls and reduced-motion preferences.
- No analytics, external JavaScript dependencies or client secrets.

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

The site is live at https://rahv-fb.github.io/nhtsa-stats-US/ (Repository Settings → Pages → Source: GitHub Actions). The verify job also runs on pull requests that touch website/, reports/, docs/ or outputs/tables/, so a stale snapshot or a hard-coded statistic that no longer matches its table fails CI before merge.

## Scientific provenance

The canonical source of every displayed data value is the project's generated source reports and output tables. The public data copies are mapped by website/tools/sync_public_data.py and checked by CI. Do not manually change website/data.

When analysis results change, regenerate reports using the established research pipeline, synchronize the public snapshots and review the explanatory text for alignment. Never turn adjusted associations, selected drug observations or hypothetical policy scenarios into causal claims.

The nine-page technical interface remains runnable through: uv run streamlit run app/streamlit_app.py

The research cannot measure risk per journey or kilometre, intervention effects, selective drug-testing biases away, or individual causal shares of deaths.
