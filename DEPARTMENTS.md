# The department-level model: design, data, and caveats

Built 13 August 2026 (this document began as a feasibility note; the system it
describes is now live at `departments.html`, with estimates in
`data/dept_latent_scores.csv` and `data/dept_item_parameters.csv`).

## What it is

The same measurement model as the university page — every ranking a noisy,
censored instrument on a latent scale, theta following a random walk — fit
separately within each of 57 academic fields (the ShanghaiRanking GRAS subject
taxonomy, plus one THE-only humanities field). 57 fields fitted; Robotics was
skipped (a single 100-row edition cannot support a fit). Roughly 971,000
field-institution-year estimates over 2012-2025.

## Instruments

**GRAS** (ShanghaiRanking Global Ranking of Academic Subjects): 57 subjects,
editions 2017-2025, pulled complete from the public JSON API
(`code/00_fetch_shanghai_api.py gras`). Exact ranks to 50, bands to 200-500.
The narrow-field spine: every GRAS subject is its own field.

**THE subject tables**: 11 broad subjects, editions 2020-2026, pulled from the
ranking-table JSON endpoints (`code/00c_fetch_the_subjects.py`), with overall
scores, ~750-1,200 institutions each. Attached to constituent GRAS fields via
the concordance in `code/20_dept_ingest.py` (THE_MAP).

**Leiden main fields**: 5 broad fields, editions 2015-2023, from the official
edition files (PP top 10%, fractional counting, most recent window,
`code/00d_convert_leiden.py`). Institutions enter a field only with at least
100 publications in the window, so a stellar top-10% share on a token output
does not fabricate a department. Attached via LEIDEN_MAP.

**QS World University Rankings by Subject**: 60 subjects, editions 2011-2026,
recovered from QS's own JSON endpoints (live and Wayback-archived), the
official 2026 results file, and archived page tables (569 subject-year files,
~165k listings; the main remaining gap is 2022-2025 for ~17 social-science
subjects, documented in the collection's SOURCE.txt). QS subjects are narrow,
so most map one-to-one onto GRAS fields (QS_MAP in code/20_dept_ingest.py);
QS's humanities subjects feed the THE-only humanities field. QS extends most
fields' coverage back to 2011.

Where a broad instrument maps to several narrow fields the same listing is
reused in each; fields are fit independently, so nothing is double-counted
within a fit.

## Entity resolution

Reuses the university-level crosswalk (exact raw-name match, then the shared
normaliser in `code/namenorm.py` against the crosswalk key). 99.6% of subject
listings resolve to an institution already in the university panel, which also
links every department series to its university's overall theta.

## How to read it

- Units are one first-observed-year standard deviation within the field.
  Compare institutions and years inside a field, never levels across fields.
- A field-year's estimate pools 1-3 instruments; the per-field instrument
  table (shown on the page) reports each system's estimated reliability in
  that field. Single-instrument fields are smoothed versions of that
  instrument, and are labelled as such on the page.
- The construct caveat is real and disclosed: a THE broad-field score reflects
  the whole faculty, a Leiden field rank reflects publication impact, GRAS
  reflects narrow-subject research output. The per-field discrimination
  parameters absorb the mismatch; they do not make the constructs identical.

## The university anchor and rank intervals

Each department's initial state carries an informative prior centred on its
university's overall theta: theta_dept[i, 1] ~ N(b_f u_i, 0.6^2), with u_i the
university-model estimate standardised within the field and b_f a per-field
loading estimated in the sampler (dept_anchor.csv reports it; it ranges from
~2 in mathematics down to ~0 in a few niche fields). Departments the ranking
systems barely see borrow strength from what the fourteen university-level
systems say about their institution; the data overrides the prior wherever
listings exist. Within-field ranks are reported with 95% credible intervals
computed by ranking institutions inside every posterior draw.

## Possible extensions

US News subject rankings and NTU/URAP field rankings could follow the same
broad- or narrow-field attachment logic. The QS 2022-2025 social-science gap
may close if the Wayback rate-limit resets (resumable fetcher parked with the
collection). A fully joint university-department model (rather than the
anchored two-stage fit) is the main remaining modelling extension.
