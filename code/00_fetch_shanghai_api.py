"""
00_fetch_shanghai_api.py -- Pull complete ARWU (and optionally GRAS subject)
rankings straight from the public ShanghaiRanking JSON API.

Replaces the Channel-B WebFetch transcriptions of 2023-2025, which truncated
partway through the 201-300 band (see data/SOURCES.txt). A direct HTTP client
streams the full ~1 MB payload, so all 1,000 institutions per edition arrive,
with no transcription step and no band-inference caveats.

Run manually (no scheduled workflows):

    python3 00_fetch_shanghai_api.py arwu 2023 2024 2025      # world ranking
    python3 00_fetch_shanghai_api.py gras 2024                 # every subject, one year
    python3 00_fetch_shanghai_api.py gras-list                 # subject codes + years

ARWU output goes to ~/uniranks/raw2/arwu/arwu_{year}_api.csv in exactly the
column layout 01_ingest.py already reads for the arwu_*.csv glob:
    year, rank_display, rank_low, rank_high, is_band, institution, region,
    total_score
Remove the old truncated arwu_{year}_webfetch.csv files after checking the new
pull, or the glob will ingest both.

GRAS output goes to ~/uniranks/raw2/gras/gras_{year}_{subj_code}.csv, one file
per subject, for the department-level extension.

Endpoints (parameter is subj_code, not subject -- an empty rankings array with
code 200 means the subject code or parameter name is wrong, not that data is
missing):
    https://www.shanghairanking.com/api/pub/v1/arwu/rank?version={year}
    https://www.shanghairanking.com/api/pub/v1/gras/rank?version={year}&subj_code={code}
    https://www.shanghairanking.com/api/pub/v1/gras/subj?version={year}
"""
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://www.shanghairanking.com/api/pub/v1"
OUT_ARWU = Path.home() / "uniranks" / "raw2" / "arwu"
OUT_GRAS = Path.home() / "uniranks" / "raw2" / "gras"
UA = {"User-Agent": "Mozilla/5.0 (research use; see repo README)"}


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_band(rank_display: str) -> tuple[int, int, bool]:
    s = str(rank_display).strip()
    if "-" in s:
        lo, hi = s.split("-", 1)
        return int(lo), int(hi), True
    return int(s), int(s), False


def write_rows(rows: list[dict], year: int, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "rank_display", "rank_low", "rank_high", "is_band",
                    "institution", "region", "total_score"])
        for r in rows:
            lo, hi, band = parse_band(r["ranking"])
            w.writerow([year, r["ranking"], lo, hi, int(band),
                        r["univNameEn"], r["region"],
                        r["score"] if r["score"] is not None else ""])
    print(f"  {path}  ({len(rows)} rows)")


def fetch_arwu(years: list[int]) -> None:
    for y in years:
        d = get_json(f"{BASE}/arwu/rank?version={y}")
        # an unpublished edition returns a payload with no "data" key at all
        rows = d.get("data", {}).get("rankings", []) if isinstance(d.get("data"), dict) else []
        if not rows:
            print(f"  ARWU {y}: empty payload, skipped (edition not published?)")
            continue
        write_rows(rows, y, OUT_ARWU / f"arwu_{y}_api.csv")
        time.sleep(2)


def gras_subjects(year: int) -> list[tuple[str, str, str]]:
    """(code, name, comma-separated years available) for every GRAS subject."""
    d = get_json(f"{BASE}/gras/subj?version={year}")
    out = []
    for cat in d["data"]:
        for s in cat["detail"]:
            out.append((s["code"], s["nameEn"], s["versions"]))
    return out


def fetch_gras(years: list[int]) -> None:
    # the newest catalog carries every subject with its full list of editions;
    # an older version= would silently omit subjects introduced later
    subjects = gras_subjects(max(years))
    for y in years:
        for code, name, versions in subjects:
            if str(y) not in versions.split(","):
                continue
            d = get_json(f"{BASE}/gras/rank?version={y}&subj_code={code}")
            rows = d.get("data", {}).get("rankings", []) if isinstance(d.get("data"), dict) else []
            if not rows:
                print(f"  GRAS {y} {code} {name}: empty, skipped")
                continue
            write_rows(rows, y, OUT_GRAS / f"gras_{y}_{code}.csv")
            time.sleep(2)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "arwu"
    years = [int(a) for a in sys.argv[2:]] or [2023, 2024, 2025]
    if mode == "arwu":
        fetch_arwu(years)
    elif mode == "gras":
        fetch_gras(years)
    elif mode == "gras-list":
        for code, name, versions in gras_subjects(2025):
            print(f"{code}  {name:45s} {versions}")
    else:
        raise SystemExit(f"unknown mode {mode!r}: use arwu | gras | gras-list")
