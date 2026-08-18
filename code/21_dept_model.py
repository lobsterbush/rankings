"""
21_dept_model.py -- Harmonise the department-level long file and fit the same
dynamic latent-trait model as 04_gibbs.py separately within each field.

Entity resolution reuses the university-level crosswalk: exact name_raw match
first, then the shared normaliser (namenorm.py, extracted verbatim from
02_harmonize.py) against the crosswalk's nname key. Names that resolve to no
existing institution get a stable dept-local id (D + hash of nname), so THE
and GRAS listings of the same unmatched institution still merge on nname.

Per field: theta[i, t] random walk, per-system alpha/beta/sigma, exact ranks
as points on the normal-score scale, bands as intervals, eligible-but-unlisted
as left-censored -- identical construction to 03_build_model_data.py with a
per-field reference pool. Fields fit independently; theta units are one
first-observed-year SD *within that field*, so levels are comparable within a
field over time, not across fields.

Run:  python3 21_dept_model.py [n_iter]      (default 4000, 2 chains)
Outputs in ~/uniranks/work_dept/:
  dept_latent_scores.csv    field, inst, year, theta stats, rank_in_year
  dept_item_parameters.csv  alpha, beta, sigma, reliability per field-system
  dept_fit_log.txt
"""
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import ndtr, ndtri
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from namenorm import norm_name, norm_country

W = Path(os.path.expanduser("~/uniranks/work_dept"))
REPO_DATA = Path(__file__).resolve().parent.parent / "data"
N_ITER = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
BURN, THIN, CHAINS = N_ITER // 2, 20, 2
MIN_OBS = 2                      # a dept must be listed at least twice, ever

# ---------------------------------------------------------------- harmonise
d = pd.read_csv(W / "dept_raw_long.csv")
cw = pd.read_csv(REPO_DATA / "crosswalk.csv")
by_raw = dict(zip(cw.name_raw, cw.inst_id))
by_nname = {}
for nn, gid in zip(cw.nname, cw.inst_id):          # first wins, matching 02's order
    by_nname.setdefault(nn, gid)
name_of = dict(zip(cw.inst_id, cw.inst_name))

d["nname"] = d["name_raw"].map(norm_name)
d["country"] = d["country_raw"].map(norm_country)
d["inst_id"] = d["name_raw"].map(by_raw)
m = d.inst_id.isna()
d.loc[m, "inst_id"] = d.loc[m, "nname"].map(by_nname)
m = d.inst_id.isna()
d.loc[m, "inst_id"] = "D" + d.loc[m, "nname"].map(
    lambda s: format(abs(hash(s)) % 10**10, "010d"))
d["inst_name"] = d.inst_id.map(name_of).fillna(d.name_raw)
matched = (~d.inst_id.str.startswith("D")).mean()
print(f"harmonised: {matched:.1%} of listings resolve to a crosswalk institution")

# collapse duplicate (field, system, ref_year, inst) cells, keep best rank
d = d.sort_values("rank").drop_duplicates(
    ["field_code", "system", "ref_year", "inst_id"], keep="first")

# ---------------------------------------------------- university-level anchor
# A department's initial state borrows strength from its university's overall
# standing: theta_dept[i, 1] ~ N(b_f * u_i, tau0^2), where u_i is the
# university-model theta (standardised within the field's institutions) and
# b_f is a per-field loading estimated inside the sampler. Institutions with
# no university-level estimate get the diffuse N(0, 1) prior as before.
_uni = pd.read_csv(REPO_DATA / "latent_scores.csv")
_yr = int(d.ref_year.min())
_u = _uni[_uni.year == _yr].set_index("inst_id").theta_mean
if _u.empty:
    _u = _uni[_uni.year == _uni.year.max()].set_index("inst_id").theta_mean
UNI_THETA = _u.to_dict()
print(f"anchor: university theta from {(_yr if len(_u) else '?')} for "
      f"{len(UNI_THETA)} institutions")


def zq(r, mpool):
    return norm.ppf(np.clip(1.0 - (np.asarray(r, float) - 0.5) / mpool, 1e-6, 1 - 1e-6))


def rtruncnorm(mu, sd, a, b, rng):
    al, bl = (a - mu) / sd, (b - mu) / sd
    pa, pb = ndtr(al), ndtr(bl)
    lohi = pb - pa
    u = np.clip(pa + rng.random(mu.shape) * lohi, 1e-12, 1 - 1e-12)
    out = mu + sd * ndtri(u)
    bad = (lohi <= 1e-12) | ~np.isfinite(out)
    if bad.any():
        mid = np.where(np.isfinite(a) & np.isfinite(b), (a + b) / 2,
                       np.where(np.isfinite(b), b, a))
        out = np.where(bad, mid, out)
    return np.clip(out, a, b)


def fit_field(p):
    """p: one field's rows. Returns (scores_df, items_df, note)."""
    cnt = p.groupby("inst_id").size()
    p = p[p.inst_id.isin(cnt[cnt >= MIN_OBS].index)].copy()
    if p.inst_id.nunique() < 25:
        return None, None, None, "too few institutions"
    insts = sorted(p.inst_id.unique())
    years = list(range(int(p.ref_year.min()), int(p.ref_year.max()) + 1))
    systems = sorted(p.system.unique())
    I, T, J = len(insts), len(years), len(systems)
    i_of = {v: k for k, v in enumerate(insts)}
    t_of = {v: k for k, v in enumerate(years)}
    j_of = {v: k for k, v in enumerate(systems)}
    mpool = max(2000, int(p.rank_hi.max() * 2))

    ed = (p.groupby(["system", "ref_year"])
          .agg(N=("rank", "size"), maxrank=("rank_hi", "max")).reset_index())
    ed["cut"] = zq(ed["N"] + 0.5, mpool)
    z_floor = zq(mpool, mpool)
    frame = {s: set(g.inst_id) for s, g in p.groupby("system")}

    oi, ot, oj, lo, hi, kind = [], [], [], [], [], []
    for r in p.itertuples():
        oi.append(i_of[r.inst_id]); ot.append(t_of[r.ref_year]); oj.append(j_of[r.system])
        if bool(r.banded) and not np.isnan(r.rank_hi) and r.rank_hi > r.rank_lo:
            lo.append(zq(r.rank_hi, mpool)); hi.append(zq(r.rank_lo, mpool)); kind.append(1)
        else:
            v = zq(r.rank, mpool); lo.append(v); hi.append(v); kind.append(0)
    listed = {(r.inst_id, r.system, r.ref_year) for r in p.itertuples()}
    for e in ed.itertuples():
        jj, tt = j_of[e.system], t_of[e.ref_year]
        for inst in frame[e.system]:
            if (inst, e.system, e.ref_year) in listed:
                continue
            oi.append(i_of[inst]); ot.append(tt); oj.append(jj)
            lo.append(z_floor); hi.append(e.cut); kind.append(2)
    oi, ot, oj = np.array(oi), np.array(ot), np.array(oj)
    lo, hi, kind = np.array(lo, float), np.array(hi, float), np.array(kind, np.int8)
    cell = oi * T + ot

    # university anchor for the initial state, standardised within this field
    u_raw = np.array([UNI_THETA.get(inst, np.nan) for inst in insts])
    anch = np.isfinite(u_raw)
    u = np.zeros(I)
    if anch.sum() >= 25:
        u[anch] = (u_raw[anch] - u_raw[anch].mean()) / (u_raw[anch].std() or 1.0)
    else:
        anch[:] = False
    R0 = np.where(anch, 0.6 ** 2, 1.0)      # tighter prior where anchored

    keep_theta, keep_par, keep_b = [], [], []
    for c in range(CHAINS):
        rng = np.random.default_rng(7000 + c)
        theta = rng.normal(0, 0.5, (I, T))
        alpha = np.abs(rng.normal(1, 0.2, J)) + 0.5
        beta = rng.normal(0, 0.5, J)
        sig2 = np.full(J, 1.0)
        om2 = 0.05
        b_anchor = 0.8
        z = np.where(kind == 0, lo, np.where(kind == 1, (lo + hi) / 2, hi - 0.5))
        for it in range(N_ITER):
            a_o, b_o, s_o = alpha[oj], beta[oj], np.sqrt(sig2[oj])
            mu = b_o + a_o * theta[oi, ot]
            mm = kind > 0
            z[mm] = rtruncnorm(mu[mm], s_o[mm], lo[mm], hi[mm], rng)
            prec_o = a_o ** 2 / sig2[oj]
            num_o = a_o * (z - b_o) / sig2[oj]
            P = np.bincount(cell, weights=prec_o, minlength=I * T).reshape(I, T)
            S = np.bincount(cell, weights=num_o, minlength=I * T).reshape(I, T)
            Ybar = np.zeros((I, T)); nz = P > 0
            Ybar[nz] = S[nz] / P[nz]
            mflt = np.empty((I, T)); Cflt = np.empty((I, T))
            a_t = b_anchor * u; R_t = R0.copy()
            for t in range(T):
                if t > 0:
                    a_t = mflt[:, t - 1]; R_t = Cflt[:, t - 1] + om2
                C = 1.0 / (1.0 / R_t + P[:, t])
                mflt[:, t] = C * (a_t / R_t + P[:, t] * Ybar[:, t]); Cflt[:, t] = C
            theta[:, T - 1] = mflt[:, T - 1] + np.sqrt(Cflt[:, T - 1]) * rng.standard_normal(I)
            for t in range(T - 2, -1, -1):
                h = 1.0 / (1.0 / Cflt[:, t] + 1.0 / om2)
                mu_b = h * (mflt[:, t] / Cflt[:, t] + theta[:, t + 1] / om2)
                theta[:, t] = mu_b + np.sqrt(h) * rng.standard_normal(I)
            for j in range(J):
                s = oj == j
                zz, tt2 = z[s], theta[oi[s], ot[s]]
                n = zz.size
                prec = 1 / 25.0 + n / sig2[j]
                beta[j] = (np.sum(zz - alpha[j] * tt2) / sig2[j]) / prec \
                    + rng.standard_normal() / np.sqrt(prec)
                prec = 1.0 + np.sum(tt2 ** 2) / sig2[j]
                mean = (1.0 + np.sum(tt2 * (zz - beta[j])) / sig2[j]) / prec
                alpha[j] = float(rtruncnorm(np.array([mean]), np.array([1 / np.sqrt(prec)]),
                                            np.array([1e-4]), np.array([np.inf]), rng)[0])
                ssr = float(np.sum((zz - beta[j] - alpha[j] * tt2) ** 2))
                sig2[j] = 1.0 / rng.gamma(2.0 + n / 2.0, 1.0 / (1.0 + ssr / 2.0))
            dif = np.diff(theta, axis=1)
            om2 = 1.0 / rng.gamma(2.0 + dif.size / 2.0,
                                  1.0 / (0.05 + float(np.sum(dif ** 2)) / 2.0))
            if anch.any():
                # b_anchor | theta[:,0], u  (conjugate; prior N(0.8, 0.5^2))
                uu, th0 = u[anch], theta[anch, 0]
                prec = 1 / 0.25 + float(np.sum(uu ** 2)) / (0.6 ** 2)
                mean = (0.8 / 0.25 + float(np.sum(uu * th0)) / (0.6 ** 2)) / prec
                b_anchor = mean + rng.standard_normal() / np.sqrt(prec)
            if it >= BURN and (it - BURN) % THIN == 0:
                # standardise scale against the first year within every draw
                sd0 = theta[:, 0].std()
                keep_theta.append((theta / sd0).astype(np.float32).copy())
                keep_par.append(np.concatenate([alpha, beta, np.sqrt(sig2), [np.sqrt(om2)]]))
                keep_b.append(b_anchor)

    TH = np.stack(keep_theta)            # draws x I x T
    th_m, th_s = TH.mean(0), TH.std(0)
    q = np.quantile(TH, [0.025, 0.5, 0.975], axis=0)
    # rank distribution: rank every institution within each posterior draw
    order = np.argsort(-TH, axis=1)
    RK = np.empty_like(order)
    dr = np.arange(TH.shape[0])[:, None]
    for t in range(TH.shape[2]):
        RK[dr, order[:, :, t], t] = np.arange(1, TH.shape[1] + 1)[None, :]
    rk_lo = np.quantile(RK, 0.025, axis=0).astype(int)
    rk_hi = np.quantile(RK, 0.975, axis=0).astype(int)
    nlist = p.groupby(["inst_id", "ref_year"]).size()
    meta = p.groupby("inst_id").agg(inst_name=("inst_name", "first"),
                                    country=("country", "first"))
    recs = []
    for inst in insts:
        ii = i_of[inst]
        for y in years:
            tt = t_of[y]
            recs.append((inst, meta.loc[inst, "inst_name"], meta.loc[inst, "country"],
                         y, th_m[ii, tt], th_s[ii, tt], q[0, ii, tt], q[1, ii, tt],
                         q[2, ii, tt], rk_lo[ii, tt], rk_hi[ii, tt],
                         int(nlist.get((inst, y), 0))))
    sc = pd.DataFrame(recs, columns=["inst_id", "inst_name", "country", "year",
                                     "theta_mean", "theta_sd", "theta_q025",
                                     "theta_median", "theta_q975", "rank_q025",
                                     "rank_q975", "n_listings"])
    sc["rank_in_year"] = sc.groupby("year").theta_mean.rank(ascending=False).astype(int)
    PAR = np.stack(keep_par)
    items = []
    for j, s in enumerate(systems):
        al, be, sg = PAR[:, j], PAR[:, J + j], PAR[:, 2 * J + j]
        rel = al ** 2 / (al ** 2 + sg ** 2)
        items.append((s, al.mean(), be.mean(), sg.mean(), rel.mean(),
                      np.quantile(rel, 0.025), np.quantile(rel, 0.975)))
    it_df = pd.DataFrame(items, columns=["system", "alpha", "beta", "sigma",
                                         "reliability", "rel_lo", "rel_hi"])
    bb = np.array(keep_b)
    anchor = dict(b_mean=float(bb.mean()), b_sd=float(bb.std()),
                  share_anchored=float(anch.mean()))
    note = (f"I={I} T={T} J={J} obs={len(kind)} ({(kind == 2).sum()} censored) "
            f"b={bb.mean():.2f} anchored={anch.mean():.0%}")
    return sc, it_df, anchor, note


all_sc, all_it, all_anchor, log = [], [], [], []
fields = sorted(d.field_code.unique())
t0 = time.time()
for k, fc in enumerate(fields):
    p = d[d.field_code == fc]
    fname = p.field_name.iloc[0]
    sc, it_df, anchor, note = fit_field(p)
    log.append(f"{fc} {fname}: {note}")
    print(f"[{k+1}/{len(fields)}] {fc} {fname}: {note}  [{time.time()-t0:.0f}s]", flush=True)
    if sc is None:
        continue
    sc.insert(0, "field_code", fc); sc.insert(1, "field_name", fname)
    it_df.insert(0, "field_code", fc); it_df.insert(1, "field_name", fname)
    all_sc.append(sc); all_it.append(it_df)
    all_anchor.append(dict(field_code=fc, field_name=fname, **anchor))

pd.concat(all_sc, ignore_index=True).to_csv(W / "dept_latent_scores.csv", index=False)
pd.concat(all_it, ignore_index=True).to_csv(W / "dept_item_parameters.csv", index=False)
pd.DataFrame(all_anchor).to_csv(W / "dept_anchor.csv", index=False)
open(W / "dept_fit_log.txt", "w").write("\n".join(log) + "\n")
print(f"\ndone: {len(all_sc)} fields fitted in {(time.time()-t0)/60:.1f} min")
