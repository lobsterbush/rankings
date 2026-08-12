# A latent measure of international university standing, 2003–2026

Twelve international university ranking systems, harmonised and pooled with a dynamic
Bayesian latent-trait model. Each ranking is treated as one noisy, censored instrument
reading a single underlying quantity, rather than as an answer in itself.

**Site:** `index.html` (interactive figures) · `methods.html` (method, data provenance,
validation, limitations)

## Contents

    index.html                  interactive figures, self-contained
    methods.html                the methods note
    data/
      rankings_panel_long.csv   every listing, harmonised, with a retrieval channel
      latent_scores.csv         theta posterior mean, sd, percentiles, rank, by year
      item_parameters.csv       alpha, beta, sigma, reliability per ranking
      crosswalk.csv             raw name -> institution id, all variants
      edition_summary.csv       one row per system-edition
      entity_review_candidates.csv  unresolved possible-same-entity pairs
      validation_*.csv          within-edition recovery, pairwise agreement
      sensitivity_loo.csv       leave-one-ranking-out refits
      diagnostics.txt           convergence and validation output
      SOURCES.txt               provenance for every input file
    figures/                    static versions of the main figures
    code/                       the full pipeline, 01..11

## Reading the estimates

`theta_mean` is latent standing; higher is better, and one unit is one 2003 standard
deviation across institutions. `theta_sd` and the percentile columns carry the
uncertainty. `n_listings` is how many rankings listed that institution that year; where
it is zero the estimate is the random-walk prior interpolating between observed years,
with correspondingly wide intervals — `in_sample` flags this.

Comparisons of levels across distant years rest on the item parameters being constant
over time. See the methods note for what that assumption buys and what it costs.

## Rerunning

    pip install pandas numpy scipy rapidfuzz unidecode arviz matplotlib pyreadr markdown
    cd code
    python3 01_ingest.py && python3 02_harmonize.py && python3 02b_entity_review.py \
      && python3 03_build_model_data.py && python3 04_gibbs.py 15000 \
      && python3 05_diagnostics.py && python3 06_figures.py && python3 07_dashboard.py \
      && python3 08_sensitivity.py && python3 09_memo.py && python3 10_package.py \
      && python3 11_site.py

Sampling takes about six minutes per chain on two cores. `01_ingest.py` expects the raw
source files under `~/uniranks/raw/` and `~/uniranks/raw2/`; `data/SOURCES.txt` lists
every repository, commit and source URL needed to reconstruct them.
