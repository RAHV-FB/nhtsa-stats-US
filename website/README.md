# Road Evidence — public research website

Responsive, static front end for the **FARS & CRSS 2016–2024** US road-safety study. It complements, and does not replace, the nine-page Streamlit research app.

## Included

- Editorial landing page with provenance and uncertainty.
- Searchable and filterable set of all ten Phase 1 findings (confidence intervals, denominators, robustness and limitations).
- Interactive charts for over-representation, adjusted severity, factor rankings and annual fatalities, with underlying table access.
- Analysis of overlapping counts for speed, BAC, drugs and unbelted occupants.
- Speeding, alcohol, drugs and seat-belt research explainers.
- Hypothetical policy break-even calculator computed from the committed threshold baseline (not an assumed intervention effect).
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

**One-time requirement:** In GitHub Repository Settings → Pages → Build and deployment, select **GitHub Actions** as the source. GitHub Pages is not automatically enabled by adding a workflow. The predicted default address after successful deployment is https://rahv-fb.github.io/nhtsa-stats-US/ but must not be treated as live until a deployment succeeds.

## Scientific provenance

The canonical source of every displayed data value is the project's generated source reports and output tables. The public data copies are mapped by website/tools/sync_public_data.py and checked by CI. Do not manually change website/data.

When analysis results change, regenerate reports using the established research pipeline, synchronize the public snapshots and review the explanatory text for alignment. Never turn adjusted associations, selected drug observations or hypothetical policy scenarios into causal claims.

The nine-page technical interface remains runnable through: uv run streamlit run app/streamlit_app.py

The research cannot measure risk per journey or kilometre, intervention effects, selective drug-testing biases away, or individual causal shares of deaths.
