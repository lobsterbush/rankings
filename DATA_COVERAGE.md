# Data coverage: what is in the panel, and what little remains open

Updated 13 August 2026, after the second collection pass. The panel now holds
**213,327 listings, 9,259 institutions, 14 systems, 193 system-editions,
2003-2027** (up from 77,784 listings, 7,537 institutions and 12 systems in the
first release). Every gap in the original ordered gap list has been closed or
reduced; the closures are recorded per system in `data/SOURCES.txt` and
summarised in the methods note §1.

## Coverage matrix (listings per system-edition)

| Edition | ARWU | CWUR | Leiden | NTU | NatureIndex | QS | ReutersEU | ReutersWorld | SCImago | THE | THEQS | URAP | USNews | Webometrics | Systems |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2003 | 500 |  |  |  |  |  |  |  |  |  |  |  |  |  | 1 |
| 2004 | 502 |  |  |  |  |  |  |  |  |  | 200 |  |  | 200 | 3 |
| 2005 | 500 |  |  |  |  |  |  |  |  |  | 201 |  |  | 993 | 3 |
| 2006 | 500 |  |  |  |  |  |  |  |  |  | 200 |  |  | 350 | 3 |
| 2007 | 510 |  |  | 479 |  |  |  |  |  |  | 201 |  |  | 994 | 4 |
| 2008 | 503 |  |  | 478 |  |  |  |  |  |  | 201 |  |  | 999 | 4 |
| 2009 | 501 |  |  | 479 |  |  |  |  | 300 |  | 200 |  |  | 999 | 5 |
| 2010 | 500 |  |  | 778 |  |  |  |  | 300 |  |  | 1106 |  | 800 | 5 |
| 2011 | 500 |  |  | 787 |  | 695 |  |  | 301 | 200 |  | 1552 |  | 1000 | 7 |
| 2012 | 500 | 100 | 500 | 828 |  | 866 |  |  | 300 | 402 |  | 1406 |  | 1000 | 9 |
| 2013 | 500 | 100 | 500 | 843 |  | 833 |  |  | 300 | 400 |  | 1707 |  | 1000 | 9 |
| 2014 | 500 | 1000 | 750 | 862 |  | 900 |  |  | 299 | 400 |  | 1969 |  | 1000 | 9 |
| 2015 | 500 | 1000 | 750 | 883 |  | 885 |  | 91 | 299 | 401 |  | 1641 | 150 | 1000 | 11 |
| 2016 | 500 | 1000 | 842 | 903 | 500 | 878 | 100 | 90 | 300 | 800 |  | 1959 | 150 | 1000 | 13 |
| 2017 | 800 | 1000 | 903 | 787 | 500 | 904 | 100 | 91 | 300 | 981 |  | 2500 | 150 | 1000 | 13 |
| 2018 | 1000 | 1000 | 938 | 794 | 500 | 965 | 100 | 92 | 300 | 1103 |  | 2499 | 150 | 1000 | 13 |
| 2019 | 1000 | 2000 | 963 | 791 | 500 | 989 | 100 | 92 | 299 | 1258 |  | 2500 | 150 | 999 | 13 |
| 2020 | 1000 | 2000 | 1176 | 797 | 500 | 1059 |  |  | 3896 | 1397 |  | 3000 | 1500 | 999 | 11 |
| 2021 | 1000 | 2000 | 1225 | 800 | 500 | 1152 |  |  | 4125 | 1526 |  | 3002 | 1499 | 999 | 11 |
| 2022 | 1000 | 2000 | 1318 | 990 | 500 | 1294 |  |  | 4363 | 1662 |  | 3000 | 1750 | 896 | 11 |
| 2023 | 1000 | 2000 | 1411 | 1001 | 500 | 1415 |  |  | 4532 | 1799 |  | 3000 | 2000 | 999 | 11 |
| 2024 | 1000 | 2000 |  | 1203 | 500 | 1489 |  |  | 4761 | 1907 |  | 3000 | 1011 | 899 | 10 |
| 2025 | 1000 | 2000 |  | 1233 | 3029 | 1497 |  |  | 5050 | 2092 |  | 2999 | 940 | 4995 | 10 |
| 2026 |  |  |  | 1200 | 500 | 1502 |  |  |  | 2191 |  |  | 2250 |  | 5 |
| 2027 |  |  |  |  |  | 1503 |  |  |  |  |  |  |  |  | 1 |

## What was closed in the second pass

1. ARWU 2023-2025: truncated ~231-row captures replaced with the complete
   1,000-row editions from the ShanghaiRanking JSON API; all 694 previously
   transcribed rows matched the fresh pull exactly.
2. CWUR: full published depth 2012-2025 (100/1,000/2,000 rows) parsed from
   cwur.org, replacing top-120 captures for 2016-2023.
3. NTU: complete editions 2007-2026 (479-1,233 rows) from the site's JSON
   endpoint, replacing the top-100 mirror and closing 2018-2026.
4. SCImago: 2020-2025 recovered at full depth (3,900-5,050 rows) from Wayback
   captures of the official CSV export.
5. Leiden: official edition files 2012-2023 (PP top 10%, fractional counting),
   replacing the three-edition mirror.
6. US News: 2020-2023 complete, 2024-2025 to depth ~940-1,011, from mirrors
   cross-validated row-by-row against archived usnews.com captures.
7. THE-QS 2004-2009 added as its own instrument (top 200 per year, from the
   publisher's own archived tables, spot-checked against independent mirrors).
8. QS 2011 extended to the full 695-row table; QS 2013 (833 rows) recovered.
9. Webometrics: 21 historical editions 2004-2024 (mostly top 1,000) from
   Wayback, joining the full July 2025 edition.
10. URAP added as a new system: 2017-2025 complete (2,500-3,000 rows),
    2010-2016 partial reconstructions.
11. Reuters: all nine world/Europe editions from Reuters' own archived JSON;
    Nature Index: full 500-row tables for nine editions.

## Still open, in order of value

1. Round University Ranking (2010+): JavaScript-only site, no usable archive
   found. The only reachable system entirely absent.
2. US News 2024 ranks ~918-2,250 and 2025 ranks ~938-2,250: no public dump
   exists; a resumable Wayback fetcher is parked in
   `~/uniranks/raw2/usnews/raw/` if the archive rate-limit resets.
3. URAP 2010-2016 mid-table gaps (293-894 ranks per edition): resumable
   harvester parked in `~/uniranks/raw2/urap/`. These editions contribute
   without censoring assumptions (see `code/03_build_model_data.py`,
   GAP_EDITIONS), so the gaps cost information, not correctness.
4. Reuters world 2016 top-100: no capture of the data endpoint survives.
5. Leiden 2024-2025 editions and Open Edition results beyond 2023: Zenodo
   throttling cut the downloads; `curl -C -` resume details in
   `~/uniranks/raw2/leiden_full/SOURCE.txt`.
6. Webometrics 2004 beyond rank 200 and 2006 beyond rank 350: never captured.

## Model-side notes

- Editions recovered with mid-table gaps (URAP 2010-2016, US News 2024-25) are
  flagged in `GAP_EDITIONS` so unlisted institutions there are treated as
  missing, not censored-below-the-cut; that assumption is only true for clean
  prefix captures.
- Leave-one-out refits across ten systems leave the ordering essentially
  unchanged (all-institution Spearman 0.93-0.998); no single instrument
  dominates the scale.
- 2003 remains the one single-instrument year (ARWU only); the THE-QS series
  now anchors 2004-2009 alongside ARWU and early Webometrics.
