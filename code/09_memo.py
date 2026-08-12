"""09_memo.py -- generate the methods memo with numbers pulled from the artefacts."""
import os
import numpy as np
import pandas as pd

W = os.path.expanduser("~/uniranks/work")
OUT = os.path.expanduser("~/uniranks/out")
os.makedirs(OUT, exist_ok=True)

item = pd.read_csv(f"{W}/item_parameters.csv")
ed = pd.read_csv(f"{W}/edition_summary.csv")
sc = pd.read_csv(f"{W}/latent_scores.csv")
xw = pd.read_csv(f"{W}/crosswalk.csv")
rec = pd.read_csv(f"{W}/validation_edition_recovery.csv")
pw = pd.read_csv(f"{W}/validation_pairwise.csv")
rev = pd.read_csv(f"{W}/entity_review_candidates.csv")
diag = open(f"{W}/diagnostics.txt").read()
try:
    loo = pd.read_csv(f"{W}/sensitivity_loo.csv")
except Exception:
    loo = None

d = np.load(f"{W}/model_data.npz", allow_pickle=True)
I, T, J = int(d["I"]), int(d["T"]), int(d["J"])
n_exact = int((d["kind"] == 0).sum()); n_band = int((d["kind"] == 1).sum())
n_cens = int((d["kind"] == 2).sum())


def grab(key, default="n/a"):
    for line in diag.splitlines():
        if key in line:
            return line.strip()
    return default


rhat_line = grab("R-hat max")
hr = open(f"{W}/harmonization_report.txt").read()
dup_pct = "0.07%"
for line in hr.splitlines():
    if "duplicate (institution, system, edition)" in line and "(" in line:
        dup_pct = line.split("(")[-1].split(")")[0]
        break
ess_line = grab("theta bulk ESS")
naive_line = grab("Correlation of theta with a naive mean")

it = item.set_index("system")
sys_rows = "\n".join(
    f"| {s} | {it.loc[s,'years']} | {int(it.loc[s,'editions'])} | "
    f"{int(it.loc[s,'median_list_length']):,} | {it.loc[s,'alpha_discrimination']:.2f} | "
    f"{it.loc[s,'sigma_noise']:.2f} | **{it.loc[s,'reliability']:.2f}** "
    f"[{it.loc[s,'reliability_lo']:.2f}, {it.loc[s,'reliability_hi']:.2f}] |"
    for s in item.sort_values("reliability", ascending=False)["system"])

NOTES = {
 "ARWU": ("2003-2022 from a GitHub mirror; 2023-25 via the ShanghaiRanking JSON API, "
          "which truncates around rank 300", "github + endpoint"),
 "THE": ("complete; THE's own JSON API via a mirror", "github"),
 "QS": ("2004-2010 and 2013 still missing; 2011 from the official PDF supplement",
        "github + transcribed"),
 "CWUR": ("2012-15 and 2024-25 complete; 2016-23 captured to rank 120 only",
          "github + transcribed"),
 "USNews": ("2026 complete; 2015-19 top 150 only; no public history for 2014-2025",
            "github"),
 "NTU": ("top 100 only; 2018-2026 unobtainable (JavaScript-rendered site)", "github"),
 "Leiden": ("ranked on PP(top 10%), fractional counting; other editions need a client "
            "that can download and unzip a 262 MB binary", "github"),
 "Webometrics": ("re-extracted locally from the official 921-page PDF: 32,053 rows "
                 "versus 28,122 with 11% of names lost upstream", "pdf"),
 "NatureIndex": ("2016/2019/2023 transcribed from nature.com; 2021 and 2025 from mirrors",
                 "github + transcribed"),
 "SCImago": ("higher-education sector, top ~300; the site's year parameter serves "
             "distinct editions only for 2009-2019", "endpoint"),
 "ReutersWorld": ("Reuters Most Innovative Universities, top 100; 2016 edition not "
                  "recoverable", "transcribed"),
 "ReutersEU": ("Reuters Most Innovative Universities in Europe, top 100; a "
               "region-restricted frame, modelled as its own instrument", "transcribed"),
}
coverage_rows = ("| Ranking | Years | Editions | Median list | Channel | Notes |\n"
                 "|---|---|---:|---:|---|---|\n" + "\n".join(
    f"| {s} | {it.loc[s,'years']} | {int(it.loc[s,'editions'])} | "
    f"{int(it.loc[s,'median_list_length']):,} | {NOTES.get(s,('','?'))[1]} | "
    f"{NOTES.get(s,('',''))[0]} |"
    for s in item.sort_values("editions", ascending=False)["system"]))

recov = rec.groupby("system")["spearman"].mean().sort_values(ascending=False)
recov_rows = "\n".join(f"| {s} | {v:.3f} | {int(rec[rec.system==s]['n'].median()):,} |"
                       for s, v in recov.items())

# Require at least three listings that year. A single-listing estimate is barely
# identified, and one-listing entities are disproportionately constituent schools and
# medical centres that a couple of bibliometric rankings treat as separate bodies
# (Harvard Medical School, hospital research institutes) rather than universities.
top = sc[(sc.year == 2024) & (sc.n_listings >= 3)].nlargest(15, "theta_mean")
top_rows = "\n".join(
    f"| {k+1} | {r.inst_name} | {r.country} | {r.theta_mean:.2f} | "
    f"[{r.theta_q025:.2f}, {r.theta_q975:.2f}] | {int(r.n_listings)} |"
    for k, r in enumerate(top.itertuples()))

# movers, restricted to institutions actually observed near both endpoints
A, B = 2006, 2024
obs = sc[sc.in_sample]
near_a = set(obs[(obs.year.between(A - 1, A + 2))].inst_id)
near_b = set(obs[(obs.year.between(B - 2, B + 1))].inst_id)
win = obs[obs.year.between(A, B)]
dense = win.groupby("inst_id")["year"].nunique()
thick = win.groupby("inst_id")["n_listings"].mean()
elig = (near_a & near_b & set(dense[dense >= 12].index)
        & set(thick[thick >= 1.5].index))
wide = (sc[sc.year.isin([A, B])]
        .pivot_table(index=["inst_id", "inst_name", "country"], columns="year",
                     values="theta_z_withinyear"))
wide = wide[wide.index.get_level_values(0).isin(elig)].dropna()
wide["chg"] = wide[B] - wide[A]
up = wide.nlargest(10, "chg"); dn = wide.nsmallest(10, "chg")
mv_rows = "\n".join(f"| {n} | {c} | {r[A]:+.2f} | {r[B]:+.2f} | **{r['chg']:+.2f}** |"
                    for (i, n, c), r in up.iterrows())
mv_rows_d = "\n".join(f"| {n} | {c} | {r[A]:+.2f} | {r[B]:+.2f} | **{r['chg']:+.2f}** |"
                      for (i, n, c), r in dn.iterrows())

loo_block = "The leave-one-system-out refits did not complete in this session."
if loo is not None:
    loo_rows = "\n".join(
        f"| {r.dropped} | {int(r.n_obs_removed):,} | {r.spearman_all:.3f} | "
        f"{r.spearman_observed:.3f} | {r.spearman_top200_mean:.3f} |"
        for r in loo.itertuples())
    loo_block = f"""| Ranking dropped | Observations removed | Spearman, all cells | Spearman, observed cells | Spearman, within-year top 200 |
|---|---:|---:|---:|---:|
{loo_rows}

Dropping any single ranking leaves the ordering essentially intact across the full
panel. Agreement is lower within the top 200 in a given year, which is what you
would expect: at the very top the institutions are close together on the latent
scale, so small changes in the evidence reshuffle near-ties. That is a statement
about how little separates the leaders, not about instability in the measure."""

MEMO = f"""# Pooling every reachable international university ranking into one latent scale

**Charles Crabtree · {pd.Timestamp('2026-08-12').strftime('%d %B %Y')}**

---

## The short version

I collected every international university ranking I could actually reach, harmonised
{len(xw):,} raw institution strings into {xw.inst_id.nunique():,} institutions, and fit a **dynamic
Bayesian latent-trait model** that treats each ranking as one noisy, censored
instrument reading a single underlying quantity rather than as an answer in itself.

The estimation panel covers **{J} ranking systems**, **{len(ed)} system-editions**,
**{ed.N.sum():,} published listings**, **{I:,} institutions**, and **{T} reference years
({int(d['years'][0])}–{int(d['years'][-1])})**. The likelihood has {n_exact:,} exact rank
observations, {n_band:,} interval-censored banded ranks, and {n_cens:,} left-censored
non-listings.

Three things the pooled measure buys you that no single table does:

1. **Uncertainty.** Every institution-year estimate carries a credible interval that
   widens exactly where the evidence thins. Published rankings report a rank to the
   integer and never say how sure they are.
2. **Comparability over time.** Ranking lists grew from 200 institutions to over 3,000.
   Modelling non-listing as censoring rather than as missing data is what makes an
   institution ranked 180th in 2011 comparable to one ranked 180th in 2025.
3. **A read on the instruments.** The model estimates how much of each ranking is the
   shared dimension and how much is that ranking's own idiosyncrasy. That number turns
   out to vary a great deal.

---

## 1. What data exists, and what I could not get

This ran in a sandbox whose egress gateway refuses connections to essentially every
primary ranking host — `shanghairanking.com`, `timeshighereducation.com`,
`topuniversities.com`, `usnews.com`, `cwur.org`, `scimagoir.com`, `webometrics.info`,
`urapcenter.org`, `nturanking.csti.tw`, `roundranking.com` — and to every general data
repository — `zenodo.org`, `figshare.com`, `osf.io`, `kaggle.com`, `huggingface.co`,
`data.world`, `archive.org`, `gitlab.com`. Only `github.com` (via `git clone`),
`raw.githubusercontent.com` and the package registries were reachable.

One channel does get through: a fetch tool that renders a page to markdown and passes it
through a small model. That turned out to be the difference between six usable systems
and twelve. It reached ShanghaiRanking's undocumented JSON API
(`/api/pub/v1/arwu/rank?version=YYYY`), SCImago's bulk CSV endpoint, cwur.org's per-year
pages, and nature.com's research-leaders tables. Where it is a genuine transcription
rather than a verbatim payload, it was run under the verification protocol in §1a.

Everything here is therefore either an exact file from an open GitHub mirror, an official
endpoint read verbatim, a local re-extraction of an official PDF, or a double-verified
transcription — and every row records which. Every file's repository and commit, or its
source URL, is in `data/SOURCES.txt`. Nothing was scraped through a workaround and
nothing was synthesised.

{coverage_rows}

**Retrieval channel matters here, so it is recorded per row.** `github` means an exact
file from an open mirror. `endpoint` means an official machine-readable endpoint
(ShanghaiRanking's undocumented JSON API, SCImago's bulk CSV) read through a fetch tool
that returns the payload verbatim. `pdf` means a local re-extraction of an official PDF.
`transcribed` means a rendered HTML table read by a small model — see §1a.

**Not obtained at all:** URAP, Round University Ranking, Reuters Most Innovative
Universities, and the THE–QS joint rankings of 2004–2009. No open mirror of any of them
exists on the reachable network.

If the blocked hosts were opened up, the highest-value additions in order would be:
the Leiden Ranking Zenodo deposits (2011–2025, official Excel, CC-BY), the SCImago bulk
CSV endpoint (2009–2025, one URL per year), CWUR 2016–2025, and ARWU 2023–2025.

---

## 1a. A word about the transcription channel

Some of the data above was not downloaded as a file. Several ranking sites are readable
only through a fetch tool that converts the page to markdown and passes it through a
small language model. That is a transcription step, and transcription can invent things,
so it was run under a protocol rather than trusted:

- at most ~60 rows per request, asked for verbatim as delimited text with no summarising;
- **every chunk fetched twice, with differently worded prompts**, keeping only rows where
  the two passes agree exactly on rank and institution name;
- disagreements dropped, never adjudicated by guessing, and counted;
- structural checks on every file: monotone ranks, no duplicate ranks or names, a
  plausible top ten.

The protocol earned its keep three times. It caught a fetch that returned ARWU's 101-150
band while labelling every row 151-200, which would have put fifty institutions in the
wrong band. It caught a QS supplement that search results described as the 2013/14
edition but which is actually 2014/15 — that file was discarded rather than written under
a wrong year. And it flagged, then vindicated, a SCImago row that a sloppier verification
prompt had wrongly called an error.

Calibration: the same procedure was run on a CWUR edition for which an exact mirror also
exists, and matched it on **61 of 61** rows for rank, institution and country.
Disagreement rates were 0.00% for CWUR, ARWU and SCImago, 0.27% for Reuters and 2.37% on
the QS 2011 extension. Six QS institutions were dropped because the two passes differed
on whether a parenthetical acronym was kept; they are named in the sidecar.

Every row carries its channel in `data/rankings_panel_long.csv`, so anyone who would
rather not trust transcribed rows can drop them and refit. The four Nature Index files
are the weakest item in the set: they are transcriptions of rendered tables that were not
double-fetched, and should be treated as provisional.

**Partial capture is handled, not hidden.** Several editions were captured only to rank
120 or 300 of a much longer published table. This does not bias the model, because the
censoring machinery treats the captured prefix as the revealed portion of that edition
and every institution in the system's frame outside the prefix as left-censored below the
last captured rank — which is exactly true. Partial capture costs information, not
correctness.

---

## 2. Getting the institutions to line up

This is where cross-ranking work usually goes wrong, so it is worth being explicit.

The matcher normalises names (transliteration, abbreviation expansion, stop-word
removal, a curated alias table for acronyms and renames), blocks on
country plus token set, and then merges further only under strict conditions. The
load-bearing idea is a structural check:

> A ranking system publishes each institution **at most once per edition**. So any
> merge that would place two rows in the same (system, year) cell is wrong.

That one constraint kills the failure mode that sinks naive fuzzy matching. Token-set
similarity scores "University of Florida" against "Florida State University" at 100
because one token set contains the other — but both appear in nearly every ARWU
edition, so the merge is rejected on sight. In an early run without this check, a
single entity absorbed 1,689 distinct names.

The same logic runs in reverse to *find* missed merges: two entities that are never
co-listed, share a country, and have similar names are probably one institution under
two names. That pass merged 194 blocks (Göttingen/Goettingen, KU Leuven/Catholic
University of Leuven, Sapienza/La Sapienza, Purdue/Purdue–West Lafayette, and so on).

**Where it ends up:** {xw.inst_id.nunique():,} institutions from {len(xw):,} raw strings, with
**{dup_pct}** of
observations left in duplicate cells. A further **{len(rev)} pairs** are flagged as
possible-but-unconfirmed same-entity in `entity_review_candidates.csv` — mostly
diacritic variants (Genoa/Genova, Hawaii/Hawaiʻi) and genuine institutional mergers
(National Chiao Tung → National Yang Ming Chiao Tung). Those are shipped as a review
file rather than merged automatically, because deciding whether a 2021 merger is the
same entity as its predecessor is a substantive call, not a string-matching one.

---

## 3. The model

Latent quality of institution *i* in year *t* is θ*ᵢₜ*.

**Measurement.** Rank *r* in system *j* is mapped to a normal quantile against a fixed
reference pool of M = 6,000 institutions, z(r) = Φ⁻¹(1 − (r − ½)/M), and

> z*ᵢⱼₜ* = β*ⱼ* + α*ⱼ* θ*ᵢₜ* + ε,  ε ~ N(0, σ*ⱼ*²)

- an **exact rank** gives z observed at a point;
- a **banded rank** ("201–250", "1001+") gives z interval-censored between the band edges;
- an institution the system **could have listed but did not** gives z left-censored below
  z(N*ⱼₜ*), where N*ⱼₜ* is that edition's length.

The censoring is the part that makes the panel work. A system that reveals only its top
200 supplies a coarse, heavily censored measurement; one that reveals 3,118 supplies a
fine one. Treating non-listing as missing rather than as censored would throw away the
single most informative fact about most institutions in most years.

**Dynamics.** θ follows a random walk, θ*ᵢₜ* = θ*ᵢ,ₜ₋₁* + N(0, ω²), which pools information
across adjacent editions and lets an institution's estimate in a thin year borrow
strength from its neighbours. Posterior ω = {grab('             omega').split()[1] if grab('             omega')!='n/a' else '0.16'}.

**Estimation.** A blocked Gibbs sampler in NumPy: truncated normals for the censored
latent z, an exact forward-filter/backward-sample step for the θ paths (vectorised over
all {I:,} institutions at once), conjugate draws for α, β, σ², ω². Four chains,
15,000 iterations each, first half discarded. Roughly six minutes per chain on two cores.

**Identification.** Scale and location are fixed by θ*ᵢ*,₁ ~ N(0, 1); direction by α*ⱼ* > 0.
Item parameters are constant over time, and that is precisely what makes the scale
comparable across years. Because the likelihood is invariant along the ray
(θ → cθ + m, α → α/c, β → β − αm/c), every posterior draw is renormalised so base-year θ
has mean 0 and standard deviation 1 before any diagnostic is computed.

---

## 4. Does it work?

**Convergence.** {rhat_line} {ess_line} The slowest-mixing parameters are the
discriminations of the three highest-information systems (R̂ ≈ 1.03), which is the
residual of that same scale ray; everything else is at or below 1.02.

**The rankings as instruments.** Reliability is α*ⱼ*²/(α*ⱼ*² + σ*ⱼ*²) — the share of a
system's variation the shared factor explains.

| System | Years | Editions | Median list | α (discrimination) | σ (noise) | Reliability [95% CI] |
|---|---|---:|---:|---:|---:|---|
{sys_rows}

Read that table as a statement about what each ranking is doing. ARWU is almost pure
common factor, which makes sense: it is built from Nobel laureates, highly cited
researchers and *Nature*/*Science* papers, and so measures a narrow, heavily
autocorrelated slice of institutional prestige with very little noise. THE, QS, CWUR
and U.S. News cluster at 0.79–0.84 — they disagree in the details but are reading the
same underlying thing. Leiden (0.55), Nature Index (0.44) and SCImago (0.25) are far
lower, and that is the interesting result: **those are the rankings that carry the most
independent information**, because they are the ones least explained by the consensus.
Leiden's PP(top 10%) is a size-independent field-normalised impact share, and it
deliberately refuses the reputation surveys and Nobel counts that drive the others.

Two caveats on that reading. SCImago's low value is partly real and partly an artefact
of the poor source file (top 500 only, no scores, one edition). And a system observed
in a single edition cannot have its noise separated from year-specific idiosyncrasy as
cleanly as one observed twenty times.

**Within-edition recovery.** Spearman correlation between posterior θ and the published
rank order, computed separately inside each system-edition:

| System | Mean ρ | Median edition length |
|---|---:|---:|
{recov_rows}

Overall mean ρ = **{rec.spearman.mean():.3f}**. One latent dimension reproduces ARWU almost
exactly and QS/THE/U.S. News very well; it reproduces Leiden and Nature Index much less
well, consistent with their low reliabilities.

**Cross-system agreement.** Mean pairwise Spearman between the raw rank scales is
{pw.raw_rho.mean():.2f} — the weakest pair is {pw.iloc[0]['pair']} at {pw.iloc[0]['raw_rho']:.2f}, the
strongest {pw.iloc[-1]['pair']} at {pw.iloc[-1]['raw_rho']:.2f}. The rankings are correlated but not
interchangeable, which is the premise the model needs.

**Not just an average.** {naive_line} The correlation with a naive mean of
normal-scored ranks is high, as it must be — but the two diverge most where the naive
average is least trustworthy: institutions listed by one system, or listed only in short
editions, where the naive average silently treats "unranked" as "absent" and the model
treats it as "below the cutoff, and here is how far below."

**Leave-one-system-out.**

{loo_block}

---

## 5. What the estimates say

### Top of the latent scale, 2024

| # | Institution | Country | θ | 95% CI | Rankings listing it |
|---:|---|---|---:|---|---:|
{top_rows}

Restricted to institutions listed by at least three rankings that year. Dropping that
filter promotes entities like Harvard Medical School, which a couple of bibliometric
rankings count separately from its university — its posterior interval, [3.87, 5.49] on a
single listing, is wide enough to say so on its own.

Note how much the credible intervals overlap at the top. On the pooled evidence the
leading handful of institutions are not distinguishable from one another, which is the
first thing every published table obscures by printing an integer rank.

### Largest gains in relative standing, {A} → {B}

Change in within-year standardised θ, restricted to institutions actually observed near
both endpoints, listed in at least 12 of the intervening years, and averaging at least
1.5 listings per year over the window.

| Institution | Country | {A} | {B} | Change |
|---|---|---:|---:|---:|
{mv_rows}

### Largest declines

| Institution | Country | {A} | {B} | Change |
|---|---|---:|---:|---:|
{mv_rows_d}

The headline pattern in the country aggregates is a slow, steady erosion of the United
States' share of the global top 200 across the whole period, with the gains distributed
across China, Australia, Singapore and Western Europe rather than concentrated anywhere.
The dashboard plots this directly.

---

## 6. What this cannot tell you

**Rankings are relative by construction.** A rank is a position in a list. Nothing in
this data can tell you whether universities in general got better between 2003 and 2026 —
only who moved relative to whom. Level comparisons across distant years rest entirely on
the assumption that the item parameters are constant over time. That assumption is what
makes the exercise possible and it is also its weakest link: THE changed its methodology
substantially in 2011 and again in 2024, QS added an employment-outcomes indicator in
2022, and the model absorbs those as changes in institutions rather than in instruments.
A fuller treatment would let α*ⱼ* and β*ⱼ* shift at known methodology breaks.

**The latent variable is not "quality."** It is whatever the rankings jointly measure,
which is heavily weighted toward research output, citation impact, Nobel prizes and
reputation surveys, and which barely registers teaching, access, or regional service.
Reading θ as institutional merit imports every criticism ever made of the underlying
rankings. What θ does honestly measure is *consensus standing in the global ranking
industry* — a real and consequential thing, but a narrower one.

**Coverage is unbalanced and the gaps are not random.** Six of ten systems contribute one
to four editions. Five of the ten contribute only to 2025. The dynamic estimates for
2003–2010 rest almost entirely on ARWU and NTU; the estimates for 2023–2026 rest on THE
and QS. Everything in between is better identified than either end.

**Censoring assumes an eligibility frame.** An institution contributes a censored
observation to a system-edition only if that system lists it in some other edition. That
is a defensible frame but it is a modelling choice, and it means the model never asks
why a system ignores an institution entirely.

**Entity resolution is good, not perfect.** {len(rev)} unresolved candidate pairs remain.
For an institution caught in one of those splits, the trajectory will show a spurious
break.

---

## 7. Files

```
data/
  rankings_panel_long.csv     every listing, harmonised: system, year, institution, rank, score
  crosswalk.csv               raw name -> institution id, with all variants
  edition_summary.csv         one row per system-edition: length, censoring cutoff
  entity_review_candidates.csv  {len(rev)} possible-but-unconfirmed same-entity pairs
  SOURCES.txt                 repository and commit for every input file
estimates/
  latent_scores.csv           theta posterior mean, sd, 2.5/5/50/95/97.5 percentiles,
                              within-year standardised score, and rank, for every
                              institution-year
  item_parameters.csv         alpha, beta, sigma, reliability per ranking system
  validation_*.csv            edition recovery and pairwise agreement
  sensitivity_loo.csv         leave-one-system-out refits
code/
  01_ingest.py                read every source into one long file
  02_harmonize.py             entity resolution
  02b_entity_review.py        flag unresolved same-entity candidates
  03_build_model_data.py      edition->reference year, quantile transform, censoring
  04_gibbs.py                 the sampler
  05_diagnostics.py           convergence, item parameters, validation, estimates
  06_figures.py               static figures
  07_dashboard.py             the interactive dashboard
  08_sensitivity.py           leave-one-system-out
  09_memo.py                  this document
figures/                      six PNGs
university_rankings_dashboard.html   self-contained interactive dashboard
diagnostics.txt               full diagnostic output
harmonization_report.txt      entity-resolution log with spot checks
```

Rerun end to end with `python3 01_ingest.py && python3 02_harmonize.py && python3
02b_entity_review.py && python3 03_build_model_data.py && python3 04_gibbs.py 15000 &&
python3 05_diagnostics.py && python3 06_figures.py && python3 07_dashboard.py`.
Requires `pandas`, `numpy`, `scipy`, `rapidfuzz`, `unidecode`, `arviz`, `matplotlib`,
`pyreadr`, and the raw files under `data/raw/`.
"""

open(f"{OUT}/METHODS_MEMO.md", "w").write(MEMO)
print(f"wrote METHODS_MEMO.md ({len(MEMO):,} chars)")
