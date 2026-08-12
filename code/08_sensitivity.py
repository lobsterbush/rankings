"""
08_sensitivity.py -- leave-one-system-out refits.

If the latent scale is an artefact of one dominant ranking, dropping that ranking
should move the estimates a lot. This refits the model with each major system
removed in turn and reports how far the estimates travel.
"""
import os, sys, time
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

W = os.path.expanduser("~/uniranks/work")
sys.path.insert(0, W)
import importlib.util

d = np.load(f"{W}/model_data.npz", allow_pickle=True)
systems = list(d["systems"])
idx = pd.read_csv(f"{W}/model_index.csv").sort_values("idx").reset_index(drop=True)
full = np.load(f"{W}/posterior.npz", allow_pickle=True)["theta"]
C, D, I, T = full.shape
base = full.reshape(-1, I, T).mean(0)

DROP = ["ARWU", "THE", "QS", "CWUR", "SCImago", "Leiden"]
N_IT = 2000
rows = []

for drop in DROP:
    jd = systems.index(drop)
    keep = d["j"] != jd
    sub = f"{W}/_loo_{drop}.npz"
    np.savez_compressed(sub, I=d["I"], T=d["T"], J=d["J"], M_POOL=d["M_POOL"],
                        Z_FLOOR=d["Z_FLOOR"], years=d["years"],
                        systems=d["systems"], insts=d["insts"],
                        i=d["i"][keep], t=d["t"][keep], j=d["j"][keep],
                        lo=d["lo"][keep], hi=d["hi"][keep], kind=d["kind"][keep])
    # re-import the sampler bound to the reduced data
    spec = importlib.util.spec_from_file_location("g", f"{W}/04_gibbs.py")
    m = importlib.util.module_from_spec(spec)
    sys.argv = ["x", str(N_IT)]
    old = np.load
    np.load = lambda p, **k: old(sub, **k) if p.endswith("model_data.npz") else old(p, **k)
    spec.loader.exec_module(m)
    np.load = old
    m.THIN = 10
    t0 = time.time()
    th, _ = m.run_chain(4242)
    tm = th.mean(0)
    obs_mask = np.zeros((I, T), bool)
    obs_mask[d["i"][keep], d["t"][keep]] = True
    r_all = spearmanr(base.ravel(), tm.ravel()).correlation
    r_obs = spearmanr(base[obs_mask], tm[obs_mask]).correlation
    # per-year rank agreement among the top 200
    yr = []
    for t in range(T):
        top = np.argsort(-base[:, t])[:200]
        yr.append(spearmanr(base[top, t], tm[top, t]).correlation)
    rows.append(dict(dropped=drop, n_obs_removed=int((~keep).sum()),
                     spearman_all=r_all, spearman_observed=r_obs,
                     spearman_top200_mean=float(np.nanmean(yr)),
                     minutes=(time.time() - t0) / 60))
    print(rows[-1], flush=True)
    os.remove(sub)

out = pd.DataFrame(rows)
out.to_csv(f"{W}/sensitivity_loo.csv", index=False)
print("\n", out.round(3).to_string(index=False))
