"""
03_build_model_data.py -- turn the harmonized long panel into the arrays the
latent-variable model consumes.

Two things happen here that matter substantively.

(1) EDITION YEAR -> REFERENCE YEAR.  THE, QS and U.S. News forward-date their
    editions (the "2026" THE table was published in October 2025 on 2024 data),
    while ARWU, CWUR, NTU, Leiden, Webometrics, Nature Index and SCImago label an
    edition by its publication year. We shift the forward-dated systems back one
    year so that everything in a given column of the panel refers to the same
    real-world moment.

(2) RANKS -> A COMMON LATENT SCALE, WITH EXPLICIT CENSORING.  A rank only has
    meaning relative to the list it sits in, and the lists grew enormously
    (THE published 200 institutions in 2011 and 3,118 in 2026). We therefore map
    rank r to a normal quantile against a FIXED reference pool of M institutions,

        z(r) = Phi^{-1}( 1 - (r - 0.5) / M ),

    and treat an institution that a system could have listed but did not as
    LEFT-CENSORED below z(N_jt), where N_jt is that edition's length. This is
    what makes 2011 and 2026 comparable: a system that reveals only its top 200
    supplies a coarse, heavily censored measurement; one that reveals 3,118
    supplies a fine one. Banded ranks ("201-250", "1001+") enter as interval-
    censored observations rather than as their midpoints.

Outputs: model_data.npz, model_index.csv, edition_summary.csv
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import norm

W = os.path.expanduser("~/uniranks/work")
M_POOL = 6000          # fixed reference pool for the quantile transform
MIN_OBS = 3            # institutions with fewer observations carry no signal

p = pd.read_csv(f"{W}/panel_long.csv")

# ---------------------------------------------------- (1) edition -> reference year
# THE, U.S. News and modern QS forward-date their editions (the "2026" THE table
# appeared in October 2025). QS only adopted that convention from the 2013/14
# edition; its 2011 and 2012 tables were published in the year they name, so they
# are not shifted.
FORWARD_DATED = {"THE", "USNews"}
shift = p["system"].isin(FORWARD_DATED) | ((p["system"] == "QS") & (p["year"] >= 2013))
p["ref_year"] = p["year"] - shift.astype(int)

# drop the handful of residual duplicate cells (keep the better rank)
p = p.sort_values("rank").drop_duplicates(["inst_id", "system", "ref_year"], keep="first")

# ---------------------------------------------------- universe
cnt = p.groupby("inst_id").size()
keep = set(cnt[cnt >= MIN_OBS].index)
p = p[p.inst_id.isin(keep)].copy()
print(f"modelled universe: {len(keep)} institutions with >= {MIN_OBS} observations "
      f"({len(p)} listed observations)")

insts = sorted(p.inst_id.unique())
years = list(range(int(p.ref_year.min()), int(p.ref_year.max()) + 1))
systems = sorted(p.system.unique())
I, T, J = len(insts), len(years), len(systems)
i_of = {v: k for k, v in enumerate(insts)}
t_of = {v: k for k, v in enumerate(years)}
j_of = {v: k for k, v in enumerate(systems)}
print(f"I={I} institutions  T={T} years ({years[0]}-{years[-1]})  J={J} systems")


def zq(r):
    return norm.ppf(np.clip(1.0 - (np.asarray(r, float) - 0.5) / M_POOL, 1e-6, 1 - 1e-6))


Z_FLOOR = zq(M_POOL)

# ---------------------------------------------------- editions
ed = (p.groupby(["system", "ref_year"])
      .agg(N=("rank", "size"), maxrank=("rank_hi", "max")).reset_index())
ed["cut"] = zq(ed["N"] + 0.5)          # below this an institution went unlisted
ed.to_csv(f"{W}/edition_summary.csv", index=False)
print(f"{len(ed)} system-editions")

# system frames: which institutions a system ever lists (its eligibility frame)
frame = {s: set(g.inst_id) for s, g in p.groupby("system")}

# ---------------------------------------------------- observation arrays
obs_i, obs_t, obs_j, obs_lo, obs_hi, obs_kind = [], [], [], [], [], []
# kind 0 = point, 1 = interval (banded rank), 2 = left-censored (unlisted)

for _, r in p.iterrows():
    obs_i.append(i_of[r.inst_id]); obs_t.append(t_of[r.ref_year]); obs_j.append(j_of[r.system])
    if bool(r.banded) and not np.isnan(r.rank_hi) and r.rank_hi > r.rank_lo:
        obs_lo.append(zq(r.rank_hi)); obs_hi.append(zq(r.rank_lo)); obs_kind.append(1)
    else:
        v = zq(r["rank"]); obs_lo.append(v); obs_hi.append(v); obs_kind.append(0)

listed = {(r.inst_id, r.system, r.ref_year) for r in p.itertuples()}

# Editions recovered with MID-TABLE gaps (not clean prefixes): an institution
# absent from the captured rows may sit inside the gap, so "unlisted" does NOT
# imply "below the last captured rank". Left-censoring is wrong there; treat
# unlisted as missing instead. URAP 2010-2016 reconstructions and the partial
# USNews 2024/2025 editions (ref years 2023/2024 after the forward-date shift).
GAP_EDITIONS = {("URAP", y) for y in range(2010, 2017)} | {
    ("USNews", 2023), ("USNews", 2024)}

n_cens = n_gap_skipped = 0
for _, e in ed.iterrows():
    fr = frame[e.system]
    jj, tt, cut = j_of[e.system], t_of[e.ref_year], e.cut
    if (e.system, e.ref_year) in GAP_EDITIONS:
        n_gap_skipped += len(fr) - e.N
        continue
    for inst in fr:
        if (inst, e.system, e.ref_year) in listed:
            continue
        obs_i.append(i_of[inst]); obs_t.append(tt); obs_j.append(jj)
        obs_lo.append(Z_FLOOR); obs_hi.append(cut); obs_kind.append(2)
        n_cens += 1
print(f"gap editions: censoring skipped for {len(GAP_EDITIONS)} system-editions "
      f"(~{n_gap_skipped} would-be censored observations)")

obs = dict(i=np.array(obs_i, np.int32), t=np.array(obs_t, np.int32),
           j=np.array(obs_j, np.int32), lo=np.array(obs_lo, float),
           hi=np.array(obs_hi, float), kind=np.array(obs_kind, np.int8))
print(f"observations: {(obs['kind']==0).sum()} exact, {(obs['kind']==1).sum()} banded, "
      f"{n_cens} censored-unlisted  = {len(obs['i'])} total")

np.savez_compressed(f"{W}/model_data.npz", I=I, T=T, J=J, M_POOL=M_POOL,
                    Z_FLOOR=Z_FLOOR, years=np.array(years),
                    systems=np.array(systems, dtype=object), insts=np.array(insts, dtype=object),
                    **obs)

idx = (p.groupby("inst_id").agg(inst_name=("inst_name", "first"),
                                country=("inst_country", "first"),
                                n_obs=("rank", "size"),
                                n_sys=("system", "nunique"),
                                first_year=("ref_year", "min"),
                                last_year=("ref_year", "max")).reset_index())
idx["idx"] = idx["inst_id"].map(i_of)
idx.sort_values("idx").to_csv(f"{W}/model_index.csv", index=False)

print("\ncoverage by system:")
print(p.groupby("system").agg(editions=("ref_year", "nunique"),
                              first=("ref_year", "min"), last=("ref_year", "max"),
                              obs=("rank", "size"),
                              insts=("inst_id", "nunique")).to_string())
