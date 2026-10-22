# Audit check scripts

Exploratory scripts behind the variable audits in `docs/audit/*.md`. Each appendix names the
scripts that support its claims. They read the interim Parquet cache (`nhtsa ingest`) and,
for a few, the processed datasets (`nhtsa features`); run them from the repository root:

```bash
POLARS_MAX_THREADS=2 uv run python scripts/audit/<script>.py
```

Intermediate files are written under `/tmp/nhtsa-audit/`. These are one-off checks kept for
reproducibility of the audit appendices. They are not part of the `nhtsa_stats` package, its
pipeline or its tests, and are not linted.
