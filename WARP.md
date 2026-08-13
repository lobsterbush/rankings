# A latent measure of international university standing, 2003–2026

**Status:** Active

**One line:** Fourteen international university ranking systems (213k listings,
9,259 institutions) harmonised and pooled with a dynamic Bayesian latent-trait
model, plus the same model fit within 57 academic fields.

**Authors:** Charles Crabtree

## Orientation

- `index.html` — university dashboard; `departments.html` — field-level
  companion; `methods.html` — methods note, provenance, validation.
- `code/00*` — fetchers/converters (ShanghaiRanking API, THE subject
  endpoints, Leiden edition files, panel reconstruction). Run manually only.
- `code/01-12` — university pipeline. `01_ingest.py` expects raw mirrors under
  `~/uniranks/raw/` and `~/uniranks/raw2/` (provenance in `data/SOURCES.txt`);
  `04_gibbs.py` supports one-chain-per-invocation for parallel runs (~9
  min/chain at current size).
- `code/20-23` — department pipeline (ingest, per-field fits, page build).
- `DATA_COVERAGE.md` — coverage matrix and the short remaining-gap list.
- `DEPARTMENTS.md` — field-model design, concordances, caveats.

## Conventions

- All data collection is run manually; no GitHub Actions workflows for
  pipelines (the only workflow is Pages deployment).
- `theta_mean` units: one 2003 cross-institution SD (university model) or one
  first-year within-field SD (department model). Item parameters constant over
  time; that underwrites cross-year level comparisons.
- Editions recovered with mid-table gaps are listed in `GAP_EDITIONS`
  (`03_build_model_data.py`) and excluded from the censored-unlisted
  construction.
