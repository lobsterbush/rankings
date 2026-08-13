"""
20_dept_ingest.py -- Read the department-level (subject) ranking sources and
emit one long file: one row per (field, system, edition_year, institution).

Sources:
  GRAS   ~/uniranks/raw2/gras/gras_{year}_{code}.csv        57 subjects, 2017-2025
  THE    ~/uniranks/raw2/the_subjects/the_{slug}_{year}.csv 11 subjects, 2020-2026
  Leiden ~/uniranks/raw2/leiden_full/leiden_fields_long.csv 5 main fields, 2015-2023

Field taxonomy: the 57 GRAS subjects. Each THE broad-subject ranking and each
Leiden main-field ranking is attached as an additional instrument to the GRAS
fields it covers (concordances below). Where the mapping is one-to-many the
SAME listing is repeated for each constituent field; every field is modelled
separately downstream, so no observation is double-counted within a fit. THE
arts-and-humanities has no GRAS counterpart and is carried as its own field.

Construct caveat, documented rather than hidden: a THE broad-field score
reflects the whole faculty (teaching, income, citations); a Leiden main-field
rank reflects publication impact in a broad field; GRAS reflects research
output in the narrow subject. The measurement model estimates a separate
discrimination/noise for each system within each field, which is how that
mismatch is absorbed.

Output: ~/uniranks/work_dept/dept_raw_long.csv
Columns: field_code, field_name, system, year, ref_year, name_raw, country_raw,
         rank, rank_lo, rank_hi, banded, score, source_file
"""
import csv
import glob
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW2 = Path(os.path.expanduser("~/uniranks/raw2"))
OUT = Path(os.path.expanduser("~/uniranks/work_dept"))
OUT.mkdir(parents=True, exist_ok=True)
REPO_DATA = Path(__file__).resolve().parent.parent / "data"

SUBJECTS = {r["code"]: (r["subject"], r["category"])
            for r in csv.DictReader(open(REPO_DATA / "raw_supplement" / "gras_subjects.csv"))}

# THE slug -> GRAS field codes it plausibly instruments
THE_MAP = {
    "computer-science": ["AS0210", "AS0229"],
    "law": ["AS0503"],
    "psychology": ["AS0508"],
    "education": ["AS0506"],
    "business-and-economics": ["AS0501", "AS0509", "AS0510", "AS0511"],
    "social-sciences": ["AS0504", "AS0505", "AS0507", "AS0512"],
    "life-sciences": ["AS0301", "AS0302", "AS0303", "AS0304"],
    "clinical-and-health": ["AS0401", "AS0402", "AS0403", "AS0404", "AS0405", "AS0406"],
    "physical-sciences": ["AS0101", "AS0102", "AS0103", "AS0104", "AS0107", "AS0108"],
    "engineering": ["AS0201", "AS0202", "AS0205", "AS0211", "AS0212", "AS0213",
                    "AS0215", "AS0216", "AS0221"],
    "arts-and-humanities": ["THEAH"],       # no GRAS counterpart; own field
}
FIELD_NAMES = dict({c: n for c, (n, _) in SUBJECTS.items()},
                   THEAH="Arts & Humanities (THE only)")

# Leiden main field -> GRAS field codes it plausibly instruments (editions
# 2015-2023 use these five names; earlier vintages' variant taxonomies are
# skipped). Same broad-instrument logic and caveats as THE_MAP.
LEIDEN_MAP = {
    "Biomedical and health sciences": ["AS0401", "AS0402", "AS0403", "AS0404",
                                       "AS0405", "AS0406", "AS0302"],
    "Life and earth sciences": ["AS0301", "AS0303", "AS0304", "AS0104",
                                "AS0105", "AS0106", "AS0107", "AS0108"],
    "Mathematics and computer science": ["AS0101", "AS0210", "AS0229", "AS0502"],
    "Physical sciences and engineering": ["AS0102", "AS0103", "AS0201", "AS0202",
                                          "AS0205", "AS0211", "AS0212", "AS0213",
                                          "AS0215", "AS0221"],
    "Social sciences and humanities": ["AS0501", "AS0503", "AS0504", "AS0505",
                                       "AS0506", "AS0507", "AS0508", "AS0509",
                                       "AS0510", "AS0511", "AS0512", "THEAH"],
}

rows = []
_num = re.compile(r"\d+")


def parse_rank(s):
    """'57' -> exact; '101-150' -> band; '=87' -> exact; '1001+' -> open band."""
    s = str(s).strip().replace("–", "-").replace("=", "")
    nums = _num.findall(s)
    if not nums:
        return (np.nan, np.nan, np.nan, False)
    if len(nums) >= 2:
        lo, hi = int(nums[0]), int(nums[1])
        return ((lo + hi) / 2.0, lo, hi, True)
    v = int(nums[0])
    if s.endswith("+"):
        return (float(v), v, np.nan, True)
    return (float(v), v, v, False)


print("== GRAS")
n_gras = 0
for f in sorted(glob.glob(str(RAW2 / "gras" / "gras_*_AS*.csv"))):
    m = re.search(r"gras_(\d{4})_(AS\d+)\.csv$", f)
    year, code = int(m.group(1)), m.group(2)
    t = pd.read_csv(f)
    for r in t.itertuples():
        rk, lo, hi, band = parse_rank(r.rank_display)
        rows.append((code, FIELD_NAMES.get(code, code), "GRAS", year, year,
                     r.institution, r.region, rk, lo, hi, band,
                     r.total_score if pd.notna(r.total_score) else np.nan,
                     "shanghairanking.com GRAS API"))
    n_gras += len(t)
print(f"   {n_gras} GRAS listings")

print("== THE subjects")
n_the = 0
for f in sorted(glob.glob(str(RAW2 / "the_subjects" / "the_*_*.csv"))):
    m = re.search(r"the_([a-z-]+)_(\d{4})\.csv$", f)
    slug, year = m.group(1), int(m.group(2))
    codes = THE_MAP.get(slug)
    if codes is None:
        continue
    t = pd.read_csv(f)
    for r in t.itertuples():
        rk, lo, hi, band = parse_rank(r.rank)
        if np.isnan(rk):
            continue
        try:
            sc = float(r.scores_overall)
        except (TypeError, ValueError):
            sc = np.nan               # banded editions show score ranges; drop
        for code in codes:
            rows.append((code, FIELD_NAMES.get(code, code), "THE", year, year - 1,
                         r.name, r.location, rk, lo, hi, band, sc,
                         f"timeshighereducation.com subject tables ({slug})"))
        n_the += 1
print(f"   {n_the} THE subject listings (before field fan-out)")

print("== Leiden main fields")
n_lei = 0
_lf = RAW2 / "leiden_full" / "leiden_fields_long.csv"
if _lf.exists():
    lf = pd.read_csv(_lf)
    lf = lf[lf.field.isin(LEIDEN_MAP)]
    for r in lf.itertuples():
        for code in LEIDEN_MAP[r.field]:
            rows.append((code, FIELD_NAMES.get(code, code), "Leiden", r.year, r.year,
                         r.name_raw, r.country_raw, float(r.rank), float(r.rank),
                         float(r.rank), False, r.score,
                         f"leidenranking.com main fields ({r.field})"))
        n_lei += 1
print(f"   {n_lei} Leiden field listings (before fan-out)")

d = pd.DataFrame(rows, columns=["field_code", "field_name", "system", "year",
                                "ref_year", "name_raw", "country_raw", "rank",
                                "rank_lo", "rank_hi", "banded", "score",
                                "source_file"])
# open-ended bands: hi = edition length
for (fc, sy, y), g in d.groupby(["field_code", "system", "year"]):
    n = len(g)
    m = g.index[g.rank_hi.isna() & g.banded]
    d.loc[m, "rank_hi"] = n
    d.loc[m, "rank"] = (d.loc[m, "rank_lo"] + n) / 2.0

d.to_csv(OUT / "dept_raw_long.csv", index=False)
print("\n================ DEPT RAW LONG ================")
print(d.shape)
print(d.groupby("system").agg(fields=("field_code", "nunique"),
                              years=("year", lambda y: f"{y.min()}-{y.max()}"),
                              listings=("rank", "size")))
