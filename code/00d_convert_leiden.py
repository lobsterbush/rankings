"""
00d_convert_leiden.py -- Convert the official CWTS Leiden Ranking edition files
(xlsx/xls, downloaded to ~/uniranks/raw2/leiden_full/) into two long CSVs:

  leiden_editions_long.csv   All-sciences PP(top 10%) per university per edition
                             (consumed by 01_ingest.py; rank = PP_top10 desc)
  leiden_fields_long.csv     the same at main-field level (for the department
                             extension; five broad fields per edition 2013+)

Selection per edition, matching the convention already used for 2019-2021:
fractional counting, the most recent publication window, PP(top 10%) as the
ranking indicator. Column/sheet naming varies by vintage and is handled here;
editions still downloading (*.part) are skipped and picked up on a re-run.
"""
import os
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(os.path.expanduser("~/uniranks/raw2/leiden_full"))


def load_edition(path: Path):
    """Return (year, results-dataframe) or None."""
    m = re.search(r"(\d{4})(?:-(\d{4}))?(?:_v\d)?\.(?:xlsx|xls|zip)$", path.name)
    if not m:
        return None
    year = int(m.group(2) or m.group(1))
    if path.suffix == ".zip":
        z = zipfile.ZipFile(path)
        inner = [n for n in z.namelist() if n.endswith((".xlsx", ".xls"))]
        if not inner:
            return None
        fh = z.open(inner[0])
    else:
        fh = path
    xl = pd.ExcelFile(fh)
    sheet = next((s for s in xl.sheet_names
                  if "esults" in s or re.search(r"Ranking \d{4}$", s)), None)
    if sheet is None:
        # 2011-2012 vintage: one sheet per counting method
        sheet = next((s for s in xl.sheet_names if "Frac" in s and "all pub" in s), None)
    if sheet is None:
        return None
    return year, xl.parse(sheet)


def tidy(year: int, d: pd.DataFrame) -> pd.DataFrame | None:
    d.columns = [str(c) for c in d.columns]
    if "University" in d.columns:
        d = d.rename(columns={"University": "name_raw", "Country": "country_raw",
                              "Field": "field"})
    elif "name" in d.columns:
        d = d.rename(columns={"name": "name_raw", "country": "country_raw"})
        d["field"] = "All sciences"
    else:
        return None
    pp = next((c for c in ["PP_top10", "PP_top", "pp_top"] if c in d.columns), None)
    if pp is None:
        return None
    if "Frac_counting" in d.columns:
        f = pd.to_numeric(d["Frac_counting"], errors="coerce")
        if (f == 1).any():
            d = d[f == 1]
    if "Core_journals" in d.columns:
        # 2013 vintage publishes core-journals and all-journals variants;
        # keep the core-journals set (the headline ranking)
        c = pd.to_numeric(d["Core_journals"], errors="coerce")
        if (c == 1).any():
            d = d[c == 1]
    if "Period" in d.columns:
        d = d[d["Period"] == d["Period"].max()]
    d = d.copy()
    pub = next((c for c in ["impact_P", "P", "p"] if c in d.columns), None)
    d["pubs"] = pd.to_numeric(d[pub], errors="coerce") if pub else np.nan
    d["score"] = pd.to_numeric(d[pp], errors="coerce")
    # older vintages store shares as 0-1, newer as percent; normalise to percent
    if d["score"].max() is not np.nan and d["score"].max() <= 1.5:
        d["score"] = d["score"] * 100
    d = d.dropna(subset=["score"])
    d["year"] = year
    return d[["year", "name_raw", "country_raw", "field", "score", "pubs"]]


alls, flds = [], []
for path in sorted(SRC.iterdir()):
    if path.suffix not in {".zip", ".xlsx", ".xls"} or path.name.endswith(".part"):
        continue
    got = load_edition(path)
    if got is None:
        print(f"skip {path.name} (no results sheet)")
        continue
    year, raw = got
    d = tidy(year, raw)
    if d is None:
        print(f"skip {path.name} (unrecognised columns)")
        continue
    isall = d["field"].astype(str).str.lower().str.startswith("all")
    a = d[isall].sort_values("score", ascending=False).copy()
    a["rank"] = range(1, len(a) + 1)
    alls.append(a[["year", "rank", "name_raw", "country_raw", "score"]])
    f = d[~isall].copy()
    if len(f):
        # a PP(top 10%) share on a token publication count is noise, not a
        # department: require >= 100 publications in the field window before
        # an institution enters that field's ranking
        f = f[f["pubs"].isna() | (f["pubs"] >= 100)]
        f["rank"] = f.groupby("field")["score"].rank(ascending=False, method="first")
        flds.append(f)
    print(f"{path.name}: edition {year}, {len(a)} universities, "
          f"{f.field.nunique() if len(f) else 0} fields")

if alls:
    out = pd.concat(alls, ignore_index=True)
    out.to_csv(SRC / "leiden_editions_long.csv", index=False)
    print(f"\nwrote leiden_editions_long.csv: {len(out)} rows, "
          f"editions {out.year.min()}-{out.year.max()}")
if flds:
    out = pd.concat(flds, ignore_index=True)
    out.to_csv(SRC / "leiden_fields_long.csv", index=False)
    print(f"wrote leiden_fields_long.csv: {len(out)} rows")
