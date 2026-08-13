"""
01_ingest.py -- Read every reachable international university ranking source and
emit a single long file: one row per (system, edition_year, institution, rank).

Output: ~/uniranks/work/raw_long.csv
Columns: system, year, name_raw, country_raw, rank, rank_lo, rank_hi, banded,
         score, source_file
"""
import os, re, json, glob
import numpy as np
import pandas as pd

RAW = os.path.expanduser("~/uniranks/raw")
RAW2 = os.path.expanduser("~/uniranks/raw2")
OUT = os.path.expanduser("~/uniranks/work")
os.makedirs(OUT, exist_ok=True)
rows = []


def add(df, system, source):
    df = df.copy()
    df["system"] = system
    df["source_file"] = source
    for c in ["name_raw", "country_raw", "rank", "rank_lo", "rank_hi", "banded", "score"]:
        if c not in df:
            df[c] = np.nan
    rows.append(df[["system", "year", "name_raw", "country_raw", "rank",
                    "rank_lo", "rank_hi", "banded", "score", "source_file"]])
    print(f"  + {system:12s} {len(df):6d} rows  years {int(df.year.min())}-{int(df.year.max())}  <- {source}")


# ---------------------------------------------------------------- rank parsing
_num = re.compile(r"\d+")


def parse_rank(x):
    """Return (rank_point, lo, hi, banded). Handles '=12', '201-250', '801+', '1001+'."""
    if pd.isna(x):
        return (np.nan,) * 3 + (False,)
    s = str(x).strip().replace("–", "-").replace("—", "-")
    s = s.replace("=", "").replace("+", "-").strip()
    nums = _num.findall(s)
    if not nums:
        return (np.nan,) * 3 + (False,)
    if len(nums) == 1:
        if s.endswith("-"):          # open-ended band e.g. "1001+"
            lo = int(nums[0]); return (float(lo), lo, np.nan, True)
        v = int(nums[0]); return (float(v), v, v, False)
    lo, hi = int(nums[0]), int(nums[1])
    return ((lo + hi) / 2.0, lo, hi, True)


def expand_open_bands(df):
    """Give open-ended bands ('1001+') a hi equal to the edition's row count."""
    for (y,), g in df.groupby(["year"]):
        n = len(g)
        m = g.index[g.rank_hi.isna() & g.banded]
        df.loc[m, "rank_hi"] = n
        df.loc[m, "rank"] = (df.loc[m, "rank_lo"] + n) / 2.0
    return df


print("== THE (Times Higher Education) 2011-2026")
the = []
for f in sorted(glob.glob(f"{RAW}/the/c3nk_THE-World-University-Rankings/csv/THE_*_rankings.csv")):
    d = pd.read_csv(f)
    d = d.rename(columns={"Name": "name_raw", "Country": "country_raw", "Overall": "score"})
    pr = d["Rank"].apply(parse_rank)
    d["rank"], d["rank_lo"], d["rank_hi"], d["banded"] = zip(*pr)
    d["score"] = pd.to_numeric(d["score"], errors="coerce")
    the.append(d[["year", "name_raw", "country_raw", "rank", "rank_lo", "rank_hi", "banded", "score"]])
the = expand_open_bands(pd.concat(the, ignore_index=True))
add(the, "THE", "c3nk/THE-World-University-Rankings")


print("== QS 2012-2027")
# (a) d2ski: 2012, 2014-2022 with full indicator scores; rank = order within year
q1 = pd.read_csv(f"{RAW}/qs/d2ski_uni-ranks/QS_World_Rankings.csv")
q1 = q1.rename(columns={"University": "name_raw", "Location": "country_raw",
                        "Overall Score": "score", "Year": "year"})
q1["score"] = pd.to_numeric(q1["score"], errors="coerce")
q1 = q1.sort_values(["year", "score"], ascending=[True, False])
q1["rank"] = q1.groupby("year").cumcount() + 1
q1["rank_lo"] = q1["rank"]; q1["rank_hi"] = q1["rank"]; q1["banded"] = False
# QS publishes exact ranks only to ~400-500; below that it bands. Mark the tail.
q1.loc[q1["rank"] > 500, "banded"] = True
q1 = q1[q1.year.isin([2012, 2014, 2015])]
add(q1, "QS", "d2ski/uni-ranks (2012,2014,2015)")

# (b) ranking-radar: continuous QS rank series 2016-2027
rr = pd.read_csv(f"{RAW}/usnews/rNLKJA_ranking-radar/rankings.csv")
ru = pd.read_csv(f"{RAW}/usnews/rNLKJA_ranking-radar/universities.csv")
rr = rr.merge(ru[["id", "name", "country"]], left_on="university_id", right_on="id", how="left")
rr = rr.rename(columns={"name": "name_raw", "country": "country_raw"})
q2 = rr[rr.system == "qs"].copy()
pr = q2["rank"].apply(parse_rank)
q2["rank"], q2["rank_lo"], q2["rank_hi"], q2["banded"] = zip(*pr)
add(q2, "QS", "rNLKJA/ranking-radar (2016-2027)")


print("== ARWU / ShanghaiRanking 2003-2022")
a = pd.read_csv(f"{RAW}/arwu/ElijahSum_shanghai-ranking-complete/shanghai_results.csv")
a = a.rename(columns={"institution": "name_raw", "country_name": "country_raw",
                      "total_score": "score"})
pr = a["world_rank"].apply(parse_rank)
a["rank"], a["rank_lo"], a["rank_hi"], a["banded"] = zip(*pr)
a = expand_open_bands(a)
add(a, "ARWU", "ElijahSum/shanghai-ranking-complete")


print("== CWUR")
# Prefer the complete editions pulled straight from cwur.org (100 rows in
# 2012-2013, 1000 in 2014-2018, 2000 from 2019): full depth, exact ranks.
_cwur_full = sorted(glob.glob(f"{RAW2}/cwur/cwur_*_full.csv"))
if _cwur_full:
    cw_full = []
    for f in _cwur_full:
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "location": "country_raw",
                              "world_rank": "rank"})
        t["rank_lo"] = t["rank"]; t["rank_hi"] = t["rank"]; t["banded"] = False
        cw_full.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo",
                          "rank_hi", "banded", "score"]])
    add(pd.concat(cw_full, ignore_index=True), "CWUR", "cwur.org full editions")
else:
    c = pd.read_csv(f"{RAW}/cwur/kaggle-bundle_arnaudbenard/cwurData.csv")
    c = c.rename(columns={"institution": "name_raw", "country": "country_raw",
                          "world_rank": "rank"})
    c["rank_lo"] = c["rank"]; c["rank_hi"] = c["rank"]; c["banded"] = False
    add(c, "CWUR", "kaggle bundle / arnaudbenard")


print("== U.S. News Best Global")
u1 = rr[rr.system == "usnews"].copy()          # 2026, 2250 rows
pr = u1["rank"].apply(parse_rank)
u1["rank"], u1["rank_lo"], u1["rank_hi"], u1["banded"] = zip(*pr)
add(u1, "USNews", "rNLKJA/ranking-radar (2026)")

j = json.load(open(f"{RAW}/usnews/zequnyu_uRank/urank.json"))
ur = pd.DataFrame(j)
recs = []
for y in range(2015, 2020):
    col = f"usnews{y}"
    if col in ur:
        t = ur[["name", "region", col]].dropna().rename(
            columns={"name": "name_raw", "region": "country_raw", col: "rank"})
        t["year"] = y
        recs.append(t)
u2 = pd.concat(recs, ignore_index=True)
u2["rank_lo"] = u2["rank"]; u2["rank_hi"] = u2["rank"]; u2["banded"] = False
add(u2, "USNews", "zequnyu/uRank (2015-2019, top 150 only)")


print("== NTU Ranking")
# Prefer the full editions from the nturanking.csti.tw JSON endpoint
# (479-1233 rows per year, 2007-2026, banded below ~500).
_ntu_full = sorted(glob.glob(f"{RAW2}/ntu/ntu_*_full.csv"))
if _ntu_full:
    nt = []
    for f in _ntu_full:
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "country": "country_raw",
                              "rank_low": "rank_lo", "rank_high": "rank_hi"})
        t["banded"] = t["is_band"].astype(bool)
        t["rank"] = (t["rank_lo"] + t["rank_hi"]) / 2.0
        nt.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo",
                     "rank_hi", "banded", "score"]])
    add(pd.concat(nt, ignore_index=True), "NTU",
        "nturanking.csti.tw full editions")
else:
    n = pd.read_csv(f"{RAW}/ntu/taiwan_ranks.csv")
    n = n.rename(columns={"university": "name_raw", "total_score": "score"})
    n["rank_lo"] = n["rank"]; n["rank_hi"] = n["rank"]; n["banded"] = False
    add(n, "NTU", "jlehtoma/taiwan_rank")


print("== Webometrics 2025")
# Prefer the local re-extraction of the official 921-page PDF: 32,053 rows with
# multi-line/CJK names correctly re-joined, versus 28,122 rows with 11% of names
# lost in the upstream CSV.
_wclean = f"{RAW2}/webometrics/webometrics_2025-07_full.csv"
w = pd.read_csv(_wclean if os.path.exists(_wclean)
                else f"{RAW}/webometrics/webometrics_rankings_2025-07.csv")
w = w.rename(columns={"name": "name_raw", "world_rank": "rank"})
# ~11% of rows lost their institution name during the upstream PDF extraction and
# carry only a ROR URL; ror.org is unreachable here, so those rows are unusable.
n_bad = w["name_raw"].astype(str).str.startswith("http").sum()
w = w[~w["name_raw"].astype(str).str.startswith("http")]
print(f"   (dropped {n_bad} Webometrics rows with no recoverable name)")
w["year"] = 2025
w = w[w["rank"] <= 5000]     # tail is noise for a global-quality latent scale
w["rank_lo"] = w["rank"]; w["rank_hi"] = w["rank"]; w["banded"] = False
add(w, "Webometrics",
    "local re-extraction of the official Webometrics 2025.2 PDF"
    if os.path.exists(_wclean) else "singularityhacker/webometrics-rankings (2025.2)")


print("== Nature Index 2025")
ni = pd.read_csv(f"{RAW}/natureindex/institution-2025.csv")
ni = ni.rename(columns={"Institution": "name_raw", "Country/territory": "country_raw",
                        "Position": "rank", "Share": "score"})
ni["year"] = 2025
ni = ni[ni["rank"] <= 3000]
ni["rank_lo"] = ni["rank"]; ni["rank_hi"] = ni["rank"]; ni["banded"] = False
add(ni, "NatureIndex", "Jyotirmoyp/Nature_index_ranking (2025)")


print("== CWTS Leiden Ranking")
_leiden_full = f"{RAW2}/leiden_full/leiden_editions_long.csv"
if os.path.exists(_leiden_full):
    # official edition files (00d_convert_leiden.py): all-sciences PP(top 10%),
    # fractional counting, most recent window, ranked within edition. These
    # cover 2012-2024 and supersede the fsbmat mirror's 2019-2021.
    lf = pd.read_csv(_leiden_full)
    lf["rank_lo"] = lf["rank"]; lf["rank_hi"] = lf["rank"]; lf["banded"] = False
    add(lf[["year", "name_raw", "country_raw", "rank", "rank_lo", "rank_hi",
            "banded", "score"]], "Leiden",
        "leidenranking.com official edition files (PP top 10%)")
try:
    if os.path.exists(_leiden_full):
        raise RuntimeError("official edition files already ingested")
    import pyreadr
    lr = pyreadr.read_r(f"{RAW}/leiden/LeidenRanking/dados/LeidenRanking.Rds")
    lr = list(lr.values())[0]
    lr.columns = [str(c) for c in lr.columns]
    # keep ALL SCIENCES, fractional counting, and the most recent window per edition
    d = lr[(lr["Field"].str.upper() == "ALL SCIENCES")].copy()
    d["Per_End"] = pd.to_numeric(d["Per_End"], errors="coerce")
    d = d[d["Frac_counting"].astype(float) == 1.0] if (d["Frac_counting"].astype(float) == 1.0).any() else d
    d = d.sort_values("Per_End").groupby(["year", "University"], as_index=False).last()
    d["PP_top10"] = pd.to_numeric(d["PP_top10"], errors="coerce")
    d = d.dropna(subset=["PP_top10"])
    d["year"] = pd.to_numeric(d["year"], errors="coerce").astype(int)
    d = d.sort_values(["year", "PP_top10"], ascending=[True, False])
    d["rank"] = d.groupby("year").cumcount() + 1
    d = d.rename(columns={"University": "name_raw", "Country": "country_raw",
                          "PP_top10": "score"})
    d["rank_lo"] = d["rank"]; d["rank_hi"] = d["rank"]; d["banded"] = False
    add(d, "Leiden", "fsbmat-ufv/LeidenRanking (LR2020,LR2021; rank on PP(top 10%))")

    lr19 = pyreadr.read_r(f"{RAW}/leiden/LeidenRanking/LeidenRanking.Rds")
    lr19 = list(lr19.values())[0]
    lr19.columns = [str(c) for c in lr19.columns]
    d19 = lr19[lr19["Field"].str.upper() == "ALL SCIENCES"].copy()
    d19["Per_End"] = pd.to_numeric(d19["Per_End"], errors="coerce")
    if "Frac_counting" in d19:
        f = d19["Frac_counting"].astype(float)
        d19 = d19[f == 1.0] if (f == 1.0).any() else d19
    d19 = d19.sort_values("Per_End").groupby("University", as_index=False).last()
    d19["PP_top10"] = pd.to_numeric(d19["PP_top10"], errors="coerce")
    d19 = d19.dropna(subset=["PP_top10"]).sort_values("PP_top10", ascending=False)
    d19["rank"] = np.arange(1, len(d19) + 1)
    d19["year"] = 2019
    d19 = d19.rename(columns={"University": "name_raw", "Country": "country_raw",
                              "PP_top10": "score"})
    d19["rank_lo"] = d19["rank"]; d19["rank_hi"] = d19["rank"]; d19["banded"] = False
    add(d19, "Leiden", "fsbmat-ufv/LeidenRanking (LR2019)")
except Exception as e:
    print("  !! Leiden ingest failed:", e)



# =====================================================================
# SECOND WAVE: sources retrieved after the first pass. Several are partial
# captures of longer published tables (e.g. the top 120 of a 2,000-row CWUR
# edition). That is handled correctly downstream rather than papered over: the
# censoring model treats the captured prefix as the revealed portion of the
# edition and every institution in that system's frame that is not in the prefix
# as left-censored below the last captured rank -- which is exactly true. Partial
# capture costs information, not correctness.
# =====================================================================
if os.path.isdir(RAW2):
    print("\n===== SECOND WAVE =====")

    print("== SCImago Institutions Rankings (higher-ed sector)")
    # *_full.csv are complete direct/wayback pulls; *_top*.csv are the original
    # (or reconstructed) partial captures. Where both exist for a year, the
    # full pull wins.
    sci, sci_years = [], set()
    for pat, src in [(f"{RAW2}/scimago/scimago_*_higher-educ_full.csv",
                      "scimagoir.com full editions"),
                     (f"{RAW2}/scimago/scimago_*_higher-educ_top*.csv",
                      "scimagoir.com bulk CSV endpoint via WebFetch")]:
        part = []
        for f in sorted(glob.glob(pat)):
            y = int(re.search(r"scimago_(\d{4})_", f).group(1))
            if y in sci_years:
                continue
            sep = ";" if open(f).readline().count(";") > 1 else ","
            t = pd.read_csv(f, sep=sep)
            t.columns = [c.strip().lower() for c in t.columns]
            t = t.rename(columns={"institution": "name_raw", "country": "country_raw"})
            t["name_raw"] = t["name_raw"].astype(str).str.replace(r"\s*\*$", "", regex=True)
            t["year"] = y
            t["rank_lo"] = t["rank"]; t["rank_hi"] = t["rank"]; t["banded"] = False
            part.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo",
                           "rank_hi", "banded"]])
            sci_years.add(y)
        if part:
            add(pd.concat(part, ignore_index=True), "SCImago", src)

    print("== Nature Index annual institution tables")
    # prefer *_full.csv (complete annual tables) over the partial transcriptions;
    # 2025 already enters via the first-wave mirror, so skip it here
    ni2, ni_years = [], {2025}
    for pat in [f"{RAW2}/natureindex/natureindex_*_institutions_full.csv",
                f"{RAW2}/natureindex/natureindex_*_institutions_top*.csv"]:
        for f in sorted(glob.glob(pat)):
            y = int(re.search(r"natureindex_(\d{4})_", f).group(1))
            if y in ni_years:
                continue
            sep = "|" if open(f).readline().count("|") > 2 else ","
            t = pd.read_csv(f, sep=sep)
            t.columns = [c.strip().lower() for c in t.columns]
            nm = "institution" if "institution" in t else t.columns[1]
            t = t.rename(columns={nm: "name_raw", "country": "country_raw"})
            t["year"] = y
            t["rank_lo"] = t["rank"]; t["rank_hi"] = t["rank"]; t["banded"] = False
            ni2.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo", "rank_hi", "banded"]])
            ni_years.add(y)
    if ni2:
        add(pd.concat(ni2, ignore_index=True), "NatureIndex",
            "nature.com annual tables (full + transcribed)")

    print("== CWUR 2016-2025 (legacy top-120 transcriptions)")
    cw = []
    # the *_full.csv editions are ingested in the first wave; only pick up
    # legacy partial transcriptions here, and only for years the full pull lacks
    for f in sorted(set(glob.glob(f"{RAW2}/cwur/cwur_*.csv"))
                    - set(glob.glob(f"{RAW2}/cwur/cwur_*_full.csv"))):
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "location": "country_raw",
                              "world_rank": "rank"})
        t["rank_lo"] = t["rank"]; t["rank_hi"] = t["rank"]; t["banded"] = False
        cw.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo", "rank_hi",
                     "banded", "score"]])
    if cw:
        add(pd.concat(cw, ignore_index=True), "CWUR", "cwur.org + GitHub mirror")

    print("== ARWU 2023-2025")
    aw = []
    for f in sorted(glob.glob(f"{RAW2}/arwu/arwu_*.csv")):
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "region": "country_raw",
                              "total_score": "score"})
        t["banded"] = t["is_band"].astype(bool)
        t["rank"] = (t["rank_low"] + t["rank_high"]) / 2.0
        t = t.rename(columns={"rank_low": "rank_lo", "rank_high": "rank_hi"})
        aw.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo", "rank_hi",
                     "banded", "score"]])
    if aw:
        add(pd.concat(aw, ignore_index=True), "ARWU",
            "shanghairanking.com JSON API via WebFetch")

    print("== QS 2011")
    _q11_full = f"{RAW2}/qs/qs_2011_full.csv"
    f = _q11_full if os.path.exists(_q11_full) else f"{RAW2}/qs/qs_2011_webfetch.csv"
    if os.path.exists(f):
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "country_code": "country_raw"})
        t["banded"] = t["is_band"].astype(bool)
        t["rank"] = (t["rank_low"] + t["rank_high"]) / 2.0
        t = t.rename(columns={"rank_low": "rank_lo", "rank_high": "rank_hi"})
        if "year" not in t:
            t["year"] = 2011
        t = expand_open_bands(t)
        add(t[["year", "name_raw", "country_raw", "rank", "rank_lo", "rank_hi", "banded"]],
            "QS", "QS 2011 official PDF supplement"
            if f != _q11_full else "QS 2011 full recovered table")

    print("== Reuters Most Innovative Universities")
    # *_full.csv are complete archived lists; fall back to the transcriptions
    # only for scope-years no full list covers
    for scope, label in [("world", "ReutersWorld"), ("europe", "ReutersEU")]:
        rs, have_years = [], set()
        for pat in [f"{RAW2}/reuters/reuters_{scope}_*_full.csv",
                    f"{RAW2}/reuters/reuters_{scope}_*_webfetch.csv"]:
            for f in sorted(glob.glob(pat)):
                y = int(re.search(r"_(\d{4})_", f).group(1))
                if y in have_years:
                    continue
                t = pd.read_csv(f)
                t = t[t["institution"] != "DROPPED_TRANSCRIPTION_CONFLICT"]
                t = t.rename(columns={"institution": "name_raw", "country": "country_raw",
                                      "edition_year": "year"})
                if "year" not in t:
                    t["year"] = y
                t["rank_lo"] = t["rank"]; t["rank_hi"] = t["rank"]; t["banded"] = False
                rs.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo",
                             "rank_hi", "banded"]])
                have_years.add(y)
        if rs:
            add(pd.concat(rs, ignore_index=True), label,
                f"Reuters Most Innovative Universities ({scope})")

    print("== U.S. News Best Global 2020-2025 (recovered editions)")
    us = []
    for f in sorted(glob.glob(f"{RAW2}/usnews/usnews_*_full.csv")):
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "country": "country_raw",
                              "rank_low": "rank_lo", "rank_high": "rank_hi"})
        t["banded"] = t["is_band"].astype(bool)
        t["rank"] = (t["rank_lo"] + t["rank_hi"]) / 2.0
        us.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo",
                     "rank_hi", "banded", "score"]])
    if us:
        add(pd.concat(us, ignore_index=True), "USNews",
            "usnews.com via Wayback/mirrors (2020-2025)")

    print("== QS 2013 (recovered edition)")
    f = f"{RAW2}/qs2013/qs_2013_full.csv"
    if os.path.exists(f):
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "country": "country_raw",
                              "rank_low": "rank_lo", "rank_hi": "rank_hi",
                              "rank_high": "rank_hi"})
        t["banded"] = t["is_band"].astype(bool)
        t["rank"] = (t["rank_lo"] + t["rank_hi"]) / 2.0
        t = expand_open_bands(t)          # "701+" rows: hi = edition length
        add(t[["year", "name_raw", "country_raw", "rank", "rank_lo", "rank_hi",
               "banded", "score"]], "QS", "topuniversities.com 2013 via Wayback/mirror")

    print("== THE-QS World University Rankings 2004-2009")
    tq = []
    for f in sorted(glob.glob(f"{RAW2}/theqs/theqs_*.csv")):
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "country": "country_raw",
                              "rank_low": "rank_lo", "rank_high": "rank_hi"})
        t["banded"] = t["is_band"].astype(bool)
        t["rank"] = (t["rank_lo"] + t["rank_hi"]) / 2.0
        tq.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo",
                     "rank_hi", "banded", "score"]])
    if tq:
        add(pd.concat(tq, ignore_index=True), "THEQS",
            "THE-QS joint ranking via Wayback/mirrors (2004-2009)")

    print("== URAP world rankings")
    ura = []
    for f in sorted(glob.glob(f"{RAW2}/urap/urap_*.csv")):
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "country": "country_raw"})
        t["rank_lo"] = t["rank"]; t["rank_hi"] = t["rank"]; t["banded"] = False
        ura.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo",
                      "rank_hi", "banded", "score"]])
    if ura:
        add(pd.concat(ura, ignore_index=True), "URAP", "urapcenter.org full editions")

    print("== Webometrics historical editions")
    wh = []
    for f in sorted(glob.glob(f"{RAW2}/webometrics/webometrics_*_top*.csv")):
        t = pd.read_csv(f)
        t = t.rename(columns={"institution": "name_raw", "country": "country_raw"})
        t["rank_lo"] = t["rank"]; t["rank_hi"] = t["rank"]; t["banded"] = False
        wh.append(t[["year", "name_raw", "country_raw", "rank", "rank_lo",
                     "rank_hi", "banded"]])
    if wh:
        add(pd.concat(wh, ignore_index=True), "Webometrics",
            "webometrics.info via Wayback (historical editions)")

# ---------------------------------------------------------------------- write
long = pd.concat(rows, ignore_index=True)
long["year"] = long["year"].astype(int)
long["name_raw"] = long["name_raw"].astype(str).str.strip()
long = long[long.name_raw.str.len() > 2]
long = long.dropna(subset=["rank"])
long.to_csv(f"{OUT}/raw_long.csv", index=False)

print("\n================ RAW LONG PANEL ================")
print(long.shape)
piv = long.pivot_table(index="year", columns="system", values="rank", aggfunc="size")
print(piv.fillna(0).astype(int).to_string())
