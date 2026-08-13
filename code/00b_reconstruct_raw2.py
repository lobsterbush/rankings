"""
00b_reconstruct_raw2.py -- Regenerate lost Channel-B transcription files under
~/uniranks/raw2/ from the shipped panel (data/rankings_panel_long.csv).

The panel preserves every transcribed row verbatim (name_raw, country_raw,
rank_lo/rank_hi, banded, score, source_file), so any raw2 input whose original
file was lost can be reconstructed exactly for the rows that made it into the
panel. Only writes a family when the expected file is absent, so fresher
full-depth pulls (which supersede these) are never overwritten.

Run from code/:  python3 00b_reconstruct_raw2.py
"""
from pathlib import Path

import pandas as pd

RAW2 = Path.home() / "uniranks" / "raw2"
PANEL = Path(__file__).resolve().parent.parent / "data" / "rankings_panel_long.csv"

df = pd.read_csv(PANEL)

NOTE = ("Reconstructed 13 August 2026 from data/rankings_panel_long.csv of the "
        "published repo; rows are verbatim panel rows (source_file={src}). "
        "Superseded automatically if a fuller direct pull exists.")


def write(sub: pd.DataFrame, path: Path, src: str, cols: dict) -> None:
    if path.exists():
        print(f"skip (exists): {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame({new: sub[old] for new, old in cols.items()})
    out.to_csv(path, index=False)
    with open(path.parent / (path.stem + ".RECONSTRUCTED.txt"), "w") as f:
        f.write(NOTE.format(src=src) + "\n")
    print(f"wrote {path} ({len(out)} rows)")


base = dict(year="edition_year", institution="name_raw", country="country_raw")

# QS 2011 (PDF-supplement transcription)
s = df[df.source_file == "QS 2011 official PDF supplement"]
write(s, RAW2 / "qs" / "qs_2011_webfetch.csv", s.source_file.iloc[0] if len(s) else "",
      dict(year="edition_year", institution="name_raw", country_code="country_raw",
           rank_low="rank_lo", rank_high="rank_hi", is_band="banded", score="score"))

# Reuters world / europe
for scope, src in [("world", "Reuters Most Innovative Universities (world)"),
                   ("europe", "Reuters Most Innovative Universities (europe)")]:
    s = df[df.source_file == src]
    for y, g in s.groupby("edition_year"):
        write(g, RAW2 / "reuters" / f"reuters_{scope}_{y}_webfetch.csv", src,
              dict(edition_year="edition_year", institution="name_raw",
                   country="country_raw", rank="rank"))

# SCImago per-edition transcriptions
s = df[df.source_file == "scimagoir.com bulk CSV endpoint via WebFetch"]
for y, g in s.groupby("edition_year"):
    n = int(g["rank"].max())
    write(g, RAW2 / "scimago" / f"scimago_{y}_higher-educ_top{n}.csv", s.source_file.iloc[0],
          dict(year="edition_year", rank="rank", institution="name_raw",
               country="country_raw"))

# Nature Index 2016-2023 transcriptions
s = df[df.source_file == "nature.com research-leaders + GitHub mirror"]
for y, g in s.groupby("edition_year"):
    write(g, RAW2 / "natureindex" / f"natureindex_{y}_institutions_top{len(g)}.csv",
          s.source_file.iloc[0],
          dict(year="edition_year", rank="rank", institution="name_raw",
               country="country_raw", score="score"))

# Webometrics cleaned re-extraction (names re-joined from the PDF)
s = df[df.source_file == "local re-extraction of the official Webometrics 2025.2 PDF"]
write(s, RAW2 / "webometrics" / "webometrics_2025-07_full.csv", s.source_file.iloc[0] if len(s) else "",
      dict(world_rank="rank", name="name_raw", country="country_raw"))
