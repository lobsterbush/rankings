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

## Possible extensions

QS World University Rankings by Subject (2011+, ~55 subjects) is the longest
subject series and the natural next instrument; collection is heavier
(paginated endpoint, per-subject node ids that change by year). US News
subject rankings and NTU/URAP field rankings could follow the same broad- or
narrow-field attachment logic. A hierarchical coupling of departmental theta
to university theta (department = university + field offset) would let sparse
fields borrow strength and is the main modelling extension worth doing.
