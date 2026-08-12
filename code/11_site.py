"""
11_site.py -- assemble the GitHub Pages site.

Produces ~/uniranks/site, a self-contained static site:
    index.html        the interactive page
    methods.html      the methods note, rendered
    data/*.csv        the panel, the estimates, provenance
    figures/*.png
    .nojekyll         stop Pages running Jekyll over the output
    README.md
"""
import os, re, shutil, glob
import markdown

W = os.path.expanduser("~/uniranks/work")
OUT = os.path.expanduser("~/uniranks/out")
PKG = f"{OUT}/university_rankings_latent_measure"
SITE = os.path.expanduser("~/uniranks/site")

if os.path.isdir(SITE):
    shutil.rmtree(SITE)
for sub in ["data", "figures", "code"]:
    os.makedirs(f"{SITE}/{sub}", exist_ok=True)

shutil.copy(f"{OUT}/university_rankings_dashboard.html", f"{SITE}/index.html")
for f in glob.glob(f"{PKG}/data/*") + glob.glob(f"{PKG}/estimates/*"):
    shutil.copy(f, f"{SITE}/data/{os.path.basename(f)}")
for f in glob.glob(f"{PKG}/figures/*.png"):
    shutil.copy(f, f"{SITE}/figures/{os.path.basename(f)}")
for f in glob.glob(f"{PKG}/code/*.py"):
    shutil.copy(f, f"{SITE}/code/{os.path.basename(f)}")
open(f"{SITE}/.nojekyll", "w").write("")

# ------------------------------------------------------------------ methods page
md = open(f"{OUT}/METHODS_MEMO.md").read()
body = markdown.markdown(md, extensions=["tables", "attr_list", "sane_lists"])
# the memo's own H1 becomes the page title; drop the duplicated byline line
body = re.sub(r"<h1>(.*?)</h1>", r"<h1>\1</h1>", body, count=1)

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Methods — a latent measure of international university standing</title>
<style>
:root{--paper:#fffefb;--ink:#16150f;--ink-2:#4a4841;--ink-3:#807d73;
 --rule:#dcd9cf;--rule-2:#efece3;--link:#2a78d6;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--paper:#141310;--ink:#f4f2ea;
 --ink-2:#b7b4a8;--ink-3:#84817a;--rule:#3a382f;--rule-2:#26241e;
 --link:#3987e5;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font:16px/1.68 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.page{max-width:760px;margin:0 auto;padding:52px 26px 100px}
.nav{font-size:13.5px;color:var(--ink-3);margin-bottom:34px}
h1{font-size:27px;line-height:1.26;font-weight:600;letter-spacing:-.015em;margin:0 0 18px}
h2{font-size:17px;font-weight:600;margin:44px 0 12px;padding-top:26px;
 border-top:1px solid var(--rule)}
h3{font-size:15px;font-weight:600;margin:28px 0 8px}
p{margin:0 0 15px}
a{color:var(--link);text-decoration:none;border-bottom:1px solid currentColor}
a:hover{color:var(--ink)}
strong{font-weight:600}
code{font:13.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
 background:var(--rule-2);padding:1px 4px}
pre{background:var(--rule-2);padding:14px 16px;overflow:auto;font-size:13px;
 line-height:1.55;border-left:2px solid var(--rule)}
pre code{background:none;padding:0}
blockquote{margin:0 0 15px;padding-left:16px;border-left:2px solid var(--rule);
 color:var(--ink-2)}
ul,ol{margin:0 0 15px;padding-left:22px}
li{margin-bottom:5px}
hr{border:0;border-top:1px solid var(--rule);margin:34px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:0 0 20px;
 display:block;overflow-x:auto}
th,td{text-align:left;padding:6px 14px 6px 0;border-bottom:1px solid var(--rule-2);
 vertical-align:baseline}
thead th{color:var(--ink-3);font-weight:500;font-size:12.5px;
 border-bottom:1px solid var(--rule);white-space:nowrap}
td:first-child{white-space:nowrap}
em{color:var(--ink-2)}
</style></head><body><div class="page">
<p class="nav"><a href="index.html">← back to the figures</a></p>
__BODY__
</div></body></html>"""
open(f"{SITE}/methods.html", "w").write(PAGE.replace("__BODY__", body))

# ------------------------------------------------------------------ readme
README = """# A latent measure of international university standing, 2003–2026

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
    python3 01_ingest.py && python3 02_harmonize.py && python3 02b_entity_review.py \\
      && python3 03_build_model_data.py && python3 04_gibbs.py 15000 \\
      && python3 05_diagnostics.py && python3 06_figures.py && python3 07_dashboard.py \\
      && python3 08_sensitivity.py && python3 09_memo.py && python3 10_package.py \\
      && python3 11_site.py

Sampling takes about six minutes per chain on two cores. `01_ingest.py` expects the raw
source files under `~/uniranks/raw/` and `~/uniranks/raw2/`; `data/SOURCES.txt` lists
every repository, commit and source URL needed to reconstruct them.
"""
open(f"{SITE}/README.md", "w").write(README)

tot = sum(os.path.getsize(os.path.join(r, f))
          for r, _, fs in os.walk(SITE) for f in fs)
print(f"site built at {SITE} ({tot/1e6:.1f} MB)")
for r, _, fs in os.walk(SITE):
    for f in sorted(fs):
        p = os.path.join(r, f)
        print(f"   {os.path.relpath(p, SITE):48s} {os.path.getsize(p)/1e3:8.0f} kB")
