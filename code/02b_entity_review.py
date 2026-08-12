"""
02b_entity_review.py -- flag institution pairs that may still be the same entity.

The automated matcher is deliberately conservative, so some renames and spelling
variants survive as separate entities. This finds them by the same structural
logic used to *reject* bad merges: two entities that are never listed in the same
edition, sit in the same country, and have similar names are candidates for a
manual merge. The output is a review file, not an automatic action.
"""
import os
from collections import defaultdict
import pandas as pd
from rapidfuzz import fuzz

W = os.path.expanduser("~/uniranks/work")
p = pd.read_csv(f"{W}/panel_long.csv")
p["ref_year"] = p["year"] - p["system"].isin({"THE", "QS", "USNews"}).astype(int)
cnt = p.groupby("inst_id").size()
q = p[p.inst_id.isin(set(cnt[cnt >= 3].index))]

foot = defaultdict(set)
for r in q.itertuples():
    foot[r.inst_id].add((r.system, r.ref_year))
g = q.groupby("inst_id").agg(nm=("inst_name", "first"), c=("inst_country", "first"),
                             n=("rank", "size"), y0=("ref_year", "min"),
                             y1=("ref_year", "max"))
g["c"] = g["c"].fillna("?")

rows = []
for c, sub in g.groupby("c"):
    ids = list(sub.index)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            A, B = ids[a], ids[b]
            if foot[A] & foot[B]:
                continue                    # co-listed => certainly distinct
            s = fuzz.token_set_ratio(str(sub.nm[A]).lower(), str(sub.nm[B]).lower())
            if s >= 82:
                rows.append(dict(similarity=int(s), combined_obs=int(sub.n[A] + sub.n[B]),
                                 id_a=A, name_a=sub.nm[A], years_a=f"{sub.y0[A]}-{sub.y1[A]}",
                                 obs_a=int(sub.n[A]),
                                 id_b=B, name_b=sub.nm[B], years_b=f"{sub.y0[B]}-{sub.y1[B]}",
                                 obs_b=int(sub.n[B]), country=c))
out = pd.DataFrame(rows).sort_values("combined_obs", ascending=False)
out.to_csv(f"{W}/entity_review_candidates.csv", index=False)
print(f"{len(out)} candidate pairs for manual review -> entity_review_candidates.csv")
print(out.head(12)[["similarity", "combined_obs", "name_a", "name_b", "country"]].to_string(index=False))
