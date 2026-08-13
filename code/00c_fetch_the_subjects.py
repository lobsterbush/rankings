"""
00c_fetch_the_subjects.py -- Pull THE World University Rankings by subject from
the JSON endpoints behind the ranking tables.

For each subject page, the endpoint URL is discovered from the page HTML
(pattern /json/ranking_tables/{slug}_rankings/{year}), then fetched directly.
Output: ~/uniranks/raw2/the_subjects/the_{subject}_{year}.csv with the full
score table (rank, name, country, overall and pillar scores).

Run manually:  python3 00c_fetch_the_subjects.py 2020 2021 2022 2023 2024 2025 2026
"""
import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

SUBJECTS = [
    "arts-and-humanities", "business-and-economics", "clinical-and-health",
    "computer-science", "education", "engineering", "law", "life-sciences",
    "physical-sciences", "psychology", "social-sciences",
]
OUT = Path.home() / "uniranks" / "raw2" / "the_subjects"
UA = {"User-Agent": "Mozilla/5.0 (research use; see repo README)"}
FIELDS = ["rank", "rank_order", "name", "location", "scores_overall",
          "scores_teaching", "scores_research", "scores_citations",
          "scores_industry_income", "scores_international_outlook"]


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def discover_endpoint(subject: str, year: int) -> str | None:
    page = f"https://www.timeshighereducation.com/world-university-rankings/{year}/subject-ranking/{subject}"
    try:
        html = get(page).decode("utf-8", "replace")
    except Exception as e:
        print(f"  {subject} {year}: page fetch failed ({e})")
        return None
    m = re.search(r"https://www\.timeshighereducation\.com/json/ranking_tables/[a-z_]+/\d{4}", html)
    return m.group(0) if m else None


def main(years: list[int]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for subject in SUBJECTS:
        for year in years:
            dest = OUT / f"the_{subject}_{year}.csv"
            if dest.exists():
                print(f"  have {dest.name}")
                continue
            url = discover_endpoint(subject, year)
            if url is None:
                print(f"  {subject} {year}: no endpoint found, skipped")
                continue
            try:
                d = json.loads(get(url))
            except Exception as e:
                print(f"  {subject} {year}: json fetch failed ({e})")
                continue
            rows = d.get("data", [])
            if not rows:
                print(f"  {subject} {year}: empty, skipped")
                continue
            with open(dest, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["year", "subject"] + FIELDS)
                for r in rows:
                    w.writerow([year, subject] + [r.get(k, "") for k in FIELDS])
            print(f"  {dest.name}: {len(rows)} rows  <- {url}", flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [2026])
