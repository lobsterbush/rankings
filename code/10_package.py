"""10_package.py -- assemble the replication package."""
import os, shutil, glob, subprocess
import pandas as pd

W = os.path.expanduser("~/uniranks/work")
RAW = os.path.expanduser("~/uniranks/raw")
OUT = os.path.expanduser("~/uniranks/out")
PKG = f"{OUT}/university_rankings_latent_measure"
for sub in ["data", "estimates", "code", "figures"]:
    os.makedirs(f"{PKG}/{sub}", exist_ok=True)

# ---- data
pl = pd.read_csv(f"{W}/panel_long.csv")
_shift = (pl["system"].isin({"THE", "USNews"})
          | ((pl["system"] == "QS") & (pl["year"] >= 2013)))
pl["ref_year"] = pl["year"] - _shift.astype(int)


def _channel(src):
    s = str(src).lower()
    if "webfetch" in s and "api" in s:
        return "official_endpoint_via_webfetch"
    if "bulk csv endpoint" in s or "json api" in s:
        return "official_endpoint_via_webfetch"
    if "reuters" in s or "pdf supplement" in s or "cwur.org" in s or "nature.com" in s:
        return "webfetch_transcription"
    if "local" in s or "921-page" in s:
        return "local_pdf_extraction"
    return "github_mirror"


pl["retrieval"] = pl["source_file"].map(_channel)
pl = pl[["inst_id", "inst_name", "inst_country", "system", "year", "ref_year",
         "rank", "rank_lo", "rank_hi", "banded", "score", "name_raw",
         "country_raw", "source_file", "retrieval"]]
pl = pl.rename(columns={"year": "edition_year"})
pl.to_csv(f"{PKG}/data/rankings_panel_long.csv", index=False)
for f in ["crosswalk.csv", "edition_summary.csv", "entity_review_candidates.csv",
          "harmonization_report.txt"]:
    shutil.copy(f"{W}/{f}", f"{PKG}/data/{f}")
if os.path.exists(f"{RAW}/SOURCES.txt"):
    shutil.copy(f"{RAW}/SOURCES.txt", f"{PKG}/data/SOURCES_partial.txt")

# ---- estimates
for f in ["latent_scores.csv", "item_parameters.csv", "validation_edition_recovery.csv",
          "validation_pairwise.csv", "sensitivity_loo.csv", "diagnostics.txt"]:
    if os.path.exists(f"{W}/{f}"):
        shutil.copy(f"{W}/{f}", f"{PKG}/estimates/{f}")

# ---- code + figures
for f in sorted(glob.glob(f"{W}/[01]*.py")):
    shutil.copy(f, f"{PKG}/code/{os.path.basename(f)}")
for f in sorted(glob.glob(f"{W}/figures/*.png")):
    shutil.copy(f, f"{PKG}/figures/{os.path.basename(f)}")
shutil.copy(f"{OUT}/university_rankings_dashboard.html", f"{PKG}/")
shutil.copy(f"{OUT}/METHODS_MEMO.md", f"{PKG}/")

# ---- provenance for every raw file actually used
src = ["Provenance of every input file (retrieved 12 August 2026).",
       "All sources are open GitHub mirrors; primary ranking sites and general data",
       "repositories were unreachable from this environment. See METHODS_MEMO.md §1.", ""]
for repo in sorted(glob.glob(f"{RAW}/*/*/.git") + glob.glob(f"{RAW}/*/.git")):
    d = os.path.dirname(repo)
    try:
        url = subprocess.check_output(["git", "-C", d, "config", "--get", "remote.origin.url"],
                                      text=True).strip()
        sha = subprocess.check_output(["git", "-C", d, "rev-parse", "--short", "HEAD"],
                                      text=True).strip()
        dt = subprocess.check_output(["git", "-C", d, "log", "-1", "--format=%cs"],
                                     text=True).strip()
        src.append(f"{os.path.relpath(d, RAW):55s}  {url}  @{sha} ({dt})")
    except Exception:
        src.append(f"{os.path.relpath(d, RAW):55s}  (git metadata unavailable)")
RAW2 = os.path.expanduser("~/uniranks/raw2")
if os.path.isdir(RAW2):
    src += ["", "=== SECOND WAVE: per-file source URLs and collection notes ===", ""]
    for f in sorted(glob.glob(f"{RAW2}/*/*.source.txt") + glob.glob(f"{RAW2}/*/NOTES*.txt")
                    + glob.glob(f"{RAW2}/*/SOURCES*.txt")):
        src.append(f"--- {os.path.relpath(f, RAW2)}")
        src.append(open(f, errors="replace").read().strip())
        src.append("")
if os.path.exists(f"{RAW}/SOURCES.txt"):
    src += ["", "--- notes recorded during first-wave collection ---", ""]
    src.append(open(f"{RAW}/SOURCES.txt").read())
open(f"{PKG}/data/SOURCES.txt", "w").write("\n".join(src))

README = """# A latent measure of international university standing, 2003-2026

Twelve international university ranking systems, harmonised and pooled with a dynamic
Bayesian latent-trait model. Start with `METHODS_MEMO.md`; open
`university_rankings_dashboard.html` in a browser for the interactive version.

## What is here

    METHODS_MEMO.md                       data, model, identification, validation, limits
    university_rankings_dashboard.html    self-contained interactive dashboard

    data/
      rankings_panel_long.csv             every listing, harmonised
      crosswalk.csv                       raw name -> institution id, all variants
      edition_summary.csv                 one row per system-edition
      entity_review_candidates.csv        possible-but-unconfirmed same-entity pairs
      harmonization_report.txt            entity-resolution log with spot checks
      SOURCES.txt                         repository + commit, or source URL, for
                                          every input file, plus collection notes

    estimates/
      latent_scores.csv                   theta posterior mean, sd, percentiles, rank
      item_parameters.csv                 alpha, beta, sigma, reliability per ranking
      validation_edition_recovery.csv     within-edition rank recovery
      validation_pairwise.csv             raw cross-ranking agreement
      sensitivity_loo.csv                 leave-one-system-out refits
      diagnostics.txt                     full diagnostic output

    code/     01..10, the full pipeline
    figures/  six PNGs

## Retrieval channels

`rankings_panel_long.csv` carries a `retrieval` column so every row can be traced to
how it was obtained, and rows from weaker channels can be dropped and the model refit:

    github_mirror                   exact file from an open GitHub mirror
    official_endpoint_via_webfetch  official JSON/CSV endpoint, payload returned verbatim
    local_pdf_extraction            re-extracted locally from an official PDF
    webfetch_transcription          rendered HTML table read by a small model, under the
                                    double-fetch agreement protocol described in the memo

Some editions were captured only to rank 120 or 300 of a longer published table. That
costs information but not correctness: the censoring model treats the captured prefix as
the revealed portion of the edition and everything outside it as left-censored below the
last captured rank.

## The key columns of latent_scores.csv

    inst_id, inst_name, country, year
    theta_mean, theta_sd                  posterior mean and sd of latent standing
    theta_q025 ... theta_q975             posterior percentiles
    n_listings                            how many rankings listed it that year
    in_sample                             TRUE if n_listings > 0; elsewhere the estimate
                                          is the random-walk prior interpolating between
                                          observed years, with correspondingly wide bands
    theta_z_withinyear                    standardised within year (relative standing)
    rank_in_year                          rank on theta among all modelled institutions

Higher theta is better. The scale is fixed by theta ~ N(0,1) across institutions in
the base year (2003); one unit is one base-year standard deviation.

## Rerunning

    pip install pandas numpy scipy rapidfuzz unidecode arviz matplotlib pyreadr
    cd code
    python3 01_ingest.py && python3 02_harmonize.py && python3 02b_entity_review.py \\
      && python3 03_build_model_data.py && python3 04_gibbs.py 15000 \\
      && python3 05_diagnostics.py && python3 06_figures.py \\
      && python3 07_dashboard.py && python3 08_sensitivity.py && python3 09_memo.py

`01_ingest.py` expects the first-wave mirrors under `~/uniranks/raw/` and the
second-wave files under `~/uniranks/raw2/`; `data/SOURCES.txt`
lists every repository and commit needed to reconstruct that directory.
Sampling takes about six minutes per chain on two cores.
"""
open(f"{PKG}/README.md", "w").write(README)

z = f"{OUT}/university_rankings_latent_measure"
shutil.make_archive(z, "zip", OUT, os.path.basename(PKG))
print(f"package: {PKG}")
subprocess.run(["find", PKG, "-type", "f"], check=False)
print(f"\nzip: {z}.zip  ({os.path.getsize(z + '.zip')/1e6:.1f} MB)")
