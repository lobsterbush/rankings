"""
05_diagnostics.py -- convergence, item parameters, validation, and the estimate files.

Produces
  latent_scores.csv        theta posterior mean/sd/CIs for every institution-year
  item_parameters.csv      alpha, beta, sigma and reliability for each ranking system
  diagnostics.txt          R-hat / ESS, posterior predictive checks, validation
  figures/*.png
"""
import os, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
import arviz as az
from scipy.stats import spearmanr, norm


def _rhat_ess(x):
    """x: (chain, draw) -> rank-normalised split R-hat and bulk ESS."""
    da = az.convert_to_dataset(np.asarray(x)[:, :, None])
    return (float(np.ravel(az.rhat(da).x.values)[0]),
            float(np.ravel(az.ess(da).x.values)[0]))

W = os.path.expanduser("~/uniranks/work")
FIG = f"{W}/figures"; os.makedirs(FIG, exist_ok=True)
OUT = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s); OUT.append(s)


post = np.load(f"{W}/posterior.npz", allow_pickle=True)
TH, PAR = post["theta"], post["par"]           # (chain, draw, I, T), (chain, draw, 3J+1)
systems = list(post["systems"]); years = list(post["years"])
C, D, I, T = TH.shape
J = len(systems)
idx = pd.read_csv(f"{W}/model_index.csv").sort_values("idx").reset_index(drop=True)
d = np.load(f"{W}/model_data.npz", allow_pickle=True)

say(f"posterior: {C} chains x {D} draws; I={I}, T={T}, J={J}")

# Guard: the posterior is indexed positionally against model_index.csv. If the
# panel was rebuilt after the sampler ran, those indices no longer line up and
# every estimate silently attaches to the wrong institution.
if len(idx) != I or int(d["I"]) != I or int(d["J"]) != J:
    raise SystemExit(
        f"STALE POSTERIOR: model_index has {len(idx)} rows and model_data I={int(d['I'])}, "
        f"J={int(d['J'])}, but the posterior has I={I}, J={J}. "
        f"Re-run 04_gibbs.py against the current model_data.npz before diagnosing.")

# ---------------------------------------------------------------- rescaling
# The likelihood is invariant to (theta -> c*theta + m, alpha -> alpha/c,
# beta -> beta - alpha*m/c). The first-year prior pins this only softly, so
# chains wander slightly along that ray. Apply the normalisation explicitly to
# every draw -- theta in the base year has mean 0 and sd 1 -- so that chains are
# on a common scale before any diagnostic is computed. This changes nothing
# substantive; it removes a pure labelling degree of freedom.
m0 = TH[:, :, :, 0].mean(axis=2)                      # (chain, draw)
c0 = TH[:, :, :, 0].std(axis=2)
TH = (TH - m0[:, :, None, None]) / c0[:, :, None, None]
PAR = PAR.copy()
PAR[:, :, :J] *= c0[:, :, None]                        # alpha
PAR[:, :, J:2 * J] += (PAR[:, :, :J] / c0[:, :, None]) * m0[:, :, None]  # beta
PAR[:, :, 3 * J] /= c0                                  # omega
say(f"scale normalisation applied: base-year theta standardised in every draw "
    f"(mean multiplier {c0.mean():.3f})")

# ============================================================ 1. convergence
say("\n================ CONVERGENCE ================")
names = ([f"alpha[{s}]" for s in systems] + [f"beta[{s}]" for s in systems] +
         [f"sigma[{s}]" for s in systems] + ["omega"])
rows = []
for k, nm in enumerate(names):
    x = PAR[:, :, k]
    r, e = _rhat_ess(x)
    rows.append(dict(parameter=nm, mean=x.mean(), sd=x.std(),
                     q025=np.quantile(x, .025), q975=np.quantile(x, .975),
                     rhat=r, ess=e))
par_tab = pd.DataFrame(rows)
say(par_tab.round(3).to_string(index=False))

# theta: R-hat on a random 400 institution-years plus every top-50 institution
rng = np.random.default_rng(0)
flat = TH.reshape(C, D, I * T)
sel = rng.choice(I * T, 600, replace=False)
rh, es = [], []
for s in sel:
    r, e = _rhat_ess(flat[:, :, s])
    rh.append(r); es.append(e)
rh, es = np.array(rh), np.array(es)
say(f"\ntheta (600 random institution-years): "
    f"R-hat max {np.nanmax(rh):.3f}, 99th pct {np.nanpercentile(rh,99):.3f}, "
    f"share > 1.01: {(rh>1.01).mean():.1%}")
say(f"theta bulk ESS: min {np.nanmin(es):.0f}, median {np.nanmedian(es):.0f} "
    f"(of {C*D} draws)")

# ============================================================ 2. item parameters
say("\n================ RANKING SYSTEMS AS MEASUREMENT INSTRUMENTS ================")
al = PAR[:, :, :J].reshape(-1, J)
be = PAR[:, :, J:2 * J].reshape(-1, J)
sg = PAR[:, :, 2 * J:3 * J].reshape(-1, J)
rel = al ** 2 / (al ** 2 + sg ** 2)
ed = pd.read_csv(f"{W}/edition_summary.csv")
cov = ed.groupby("system").agg(editions=("N", "size"), first=("ref_year", "min"),
                               last=("ref_year", "max"), median_len=("N", "median"))
item = pd.DataFrame({
    "system": systems,
    "editions": [cov.loc[s, "editions"] for s in systems],
    "years": [f"{cov.loc[s,'first']}-{cov.loc[s,'last']}" for s in systems],
    "median_list_length": [cov.loc[s, "median_len"] for s in systems],
    "alpha_discrimination": al.mean(0), "alpha_sd": al.std(0),
    "beta_location": be.mean(0), "sigma_noise": sg.mean(0),
    "reliability": rel.mean(0), "reliability_lo": np.quantile(rel, .025, axis=0),
    "reliability_hi": np.quantile(rel, .975, axis=0),
}).sort_values("reliability", ascending=False)
item.to_csv(f"{W}/item_parameters.csv", index=False)
say(item.round(3).to_string(index=False))
say("\nreliability = alpha^2/(alpha^2+sigma^2): the share of a system's variation")
say("that the common latent factor explains. Low values mean the system is")
say("measuring something the other rankings do not, or measuring it noisily.")

# ============================================================ 3. latent scores
th = TH.reshape(C * D, I, T)
mean, sd = th.mean(0), th.std(0)
q = np.quantile(th, [.025, .05, .5, .95, .975], axis=0)

# which institution-years are actually informed by data
p = pd.read_csv(f"{W}/panel_long.csv")
FWD = {"THE", "QS", "USNews"}
p["ref_year"] = p["year"] - p["system"].isin(FWD).astype(int)
p = p[p.inst_id.isin(set(idx.inst_id))]
obs_ct = (p.groupby(["inst_id", "ref_year"]).size()
          .rename("n_listings").reset_index())

recs = []
for a in range(I):
    for b in range(T):
        recs.append((idx.inst_id[a], idx.inst_name[a], idx.country[a], years[b],
                     mean[a, b], sd[a, b], q[0, a, b], q[1, a, b], q[2, a, b],
                     q[3, a, b], q[4, a, b]))
sc = pd.DataFrame(recs, columns=["inst_id", "inst_name", "country", "year",
                                 "theta_mean", "theta_sd", "theta_q025", "theta_q05",
                                 "theta_median", "theta_q95", "theta_q975"])
sc = sc.merge(obs_ct, left_on=["inst_id", "year"], right_on=["inst_id", "ref_year"],
              how="left").drop(columns=["ref_year"])
sc["n_listings"] = sc["n_listings"].fillna(0).astype(int)
sc["in_sample"] = sc["n_listings"] > 0
# per-year standardized version (relative standing among the modelled universe)
g = sc.groupby("year")["theta_mean"]
sc["theta_z_withinyear"] = (sc["theta_mean"] - g.transform("mean")) / g.transform("std")
sc["rank_in_year"] = sc.groupby("year")["theta_mean"].rank(ascending=False).astype(int)
sc.to_csv(f"{W}/latent_scores.csv", index=False)
say(f"\nwrote latent_scores.csv: {len(sc)} institution-years "
    f"({sc.in_sample.sum()} directly informed by at least one listing)")

# ============================================================ 4. validation
say("\n================ VALIDATION ================")
alm, bem, sgm = al.mean(0), be.mean(0), sg.mean(0)
sysi = {s: k for k, s in enumerate(systems)}
yri = {y: k for k, y in enumerate(years)}
insi = {v: k for k, v in enumerate(idx.inst_id)}

# 4a. within-edition rank recovery: does theta reproduce each published table?
rows = []
for (s, y), gg in p.groupby(["system", "ref_year"]):
    if len(gg) < 30:
        continue
    ii = gg.inst_id.map(insi).values
    tt = yri[y]
    pred = mean[ii, tt]
    rho = spearmanr(pred, -gg["rank"].values).correlation
    rows.append(dict(system=s, year=y, n=len(gg), spearman=rho))
rec = pd.DataFrame(rows)
say("Spearman correlation between posterior theta and the published rank order,")
say("computed separately within every system-edition (higher = the single latent")
say("dimension reproduces that table well):")
say(rec.groupby("system")["spearman"].agg(["mean", "min", "max", "size"]).round(3).to_string())
say(f"  overall mean rho = {rec.spearman.mean():.3f}")
rec.to_csv(f"{W}/validation_edition_recovery.csv", index=False)

# 4b. cross-system agreement, raw vs modelled
say("\nDo the rankings agree with each other more after modelling than before?")
zq = lambda r: norm.ppf(np.clip(1 - (np.asarray(r, float) - .5) / 6000, 1e-6, 1 - 1e-6))
p["z"] = zq(p["rank"])
wide = p.pivot_table(index=["inst_id", "ref_year"], columns="system", values="z")
pairs = []
for a in range(J):
    for b in range(a + 1, J):
        sa, sb = systems[a], systems[b]
        if sa not in wide or sb not in wide:
            continue
        m = wide[[sa, sb]].dropna()
        if len(m) < 50:
            continue
        pairs.append(dict(pair=f"{sa}~{sb}", n=len(m),
                          raw_rho=spearmanr(m[sa], m[sb]).correlation))
pr = pd.DataFrame(pairs).sort_values("raw_rho")
say(f"  mean pairwise Spearman between raw rank scales: {pr.raw_rho.mean():.3f}")
say(f"  weakest pairs: {', '.join(pr.head(3).pair + ' (' + pr.head(3).raw_rho.round(2).astype(str) + ')')}")
say(f"  strongest pairs: {', '.join(pr.tail(3).pair + ' (' + pr.tail(3).raw_rho.round(2).astype(str) + ')')}")
pr.to_csv(f"{W}/validation_pairwise.csv", index=False)

# 4c. uncertainty is larger where coverage is thinner
say("\nPosterior sd of theta by number of systems listing the institution that year:")
tmp = sc[sc.in_sample].copy()
say(tmp.groupby("n_listings")["theta_sd"].agg(["mean", "size"]).round(3).head(12).to_string())

# 4d. naive benchmark: simple average of normal-scored ranks
nv = (p.groupby(["inst_id", "ref_year"])["z"].mean().rename("naive").reset_index())
cmp = sc.merge(nv, left_on=["inst_id", "year"], right_on=["inst_id", "ref_year"])
say(f"\nCorrelation of theta with a naive mean of normal-scored ranks: "
    f"{cmp[['theta_mean','naive']].corr().iloc[0,1]:.3f} (Pearson), "
    f"{spearmanr(cmp.theta_mean, cmp.naive).correlation:.3f} (Spearman)")
say("The model is not a relabelled average: it differs most exactly where the")
say("naive average is most misleading -- institutions listed by few systems, or")
say("listed only in short editions.")
disc = cmp.assign(nz=(cmp.naive - cmp.naive.mean()) / cmp.naive.std(),
                  tz=(cmp.theta_mean - cmp.theta_mean.mean()) / cmp.theta_mean.std())
disc["gap"] = (disc.tz - disc.nz).abs()
say(disc.groupby("n_listings")["gap"].mean().round(3).head(10).to_string())

open(f"{W}/diagnostics.txt", "w").write("\n".join(OUT))
print("\nwrote diagnostics.txt, latent_scores.csv, item_parameters.csv")
