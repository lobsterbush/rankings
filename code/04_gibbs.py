"""
04_gibbs.py -- Dynamic Bayesian latent-trait model for international university
rankings, estimated by a blocked Gibbs sampler with forward-filter/backward-sample.

MODEL
-----
Latent quality of institution i in year t is theta[i,t].

Measurement.  Institution i's standing in ranking system j at time t is a noisy,
system-specific linear function of theta, observed only through the rank the
system publishes:

    z[i,j,t] = beta[j] + alpha[j] * theta[i,t] + eps,      eps ~ N(0, sigma[j]^2)

    exact rank r          ->  z observed at  Phi^{-1}(1 - (r-0.5)/M)
    banded rank "201-250" ->  z in ( zq(250), zq(201) )        [interval-censored]
    eligible but unlisted ->  z < zq(N_jt)                     [left-censored]

    alpha[j] = discrimination  (how sharply system j tracks latent quality)
    beta[j]  = difficulty/location of system j's scale
    sigma[j] = idiosyncratic noise; alpha[j]^2 / (alpha[j]^2 + sigma[j]^2) is the
               share of system j's variance attributable to the common factor.

Dynamics.  theta follows a random walk, which pools information across years and
lets an institution's estimate borrow strength from adjacent editions:

    theta[i,1] ~ N(0, 1)                 <- the identifying restriction
    theta[i,t] = theta[i,t-1] + N(0, omega^2)

IDENTIFICATION.  Scale and location are fixed by theta[i,1] ~ N(0,1); direction by
alpha[j] > 0. Item parameters are constant over time, which is what makes the
scale comparable across years -- see the methods memo for what that assumption
buys and what it costs.

SAMPLER.  Five blocks:
  1. latent z for interval- and left-censored observations (truncated normals)
  2. theta | z          -- exact FFBS, vectorised over all institutions at once
  3. alpha, beta | z, theta -- conjugate, alpha drawn from a positive-truncated normal
  4. sigma^2 | .        -- inverse gamma
  5. omega^2 | theta    -- inverse gamma
"""
import os, sys, time
import numpy as np
from scipy.special import ndtr, ndtri

W = os.path.expanduser("~/uniranks/work")
d = np.load(f"{W}/model_data.npz", allow_pickle=True)
I, T, J = int(d["I"]), int(d["T"]), int(d["J"])
oi, ot, oj = d["i"].astype(np.int64), d["t"].astype(np.int64), d["j"].astype(np.int64)
lo, hi, kind = d["lo"], d["hi"], d["kind"]
years, systems = d["years"], d["systems"]
N = len(oi)
cell = oi * T + ot                                  # flat (institution, year) index

N_ITER = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
BURN = N_ITER // 2
THIN = 25
CHAINS = 4

# priors
A_ALPHA, S_ALPHA = 1.0, 1.0          # alpha ~ N+(1, 1)
S_BETA = 5.0                          # beta  ~ N(0, 5^2)
A_SIG, B_SIG = 2.0, 1.0               # sigma^2 ~ InvGamma
A_OM, B_OM = 2.0, 0.05                # omega^2 ~ InvGamma
TAU0 = 1.0                            # sd of theta in the first year


def rtruncnorm(mu, sd, a, b, rng):
    """Vectorised truncated normal via the inverse CDF, tail-safe."""
    al, bl = (a - mu) / sd, (b - mu) / sd
    pa, pb = ndtr(al), ndtr(bl)
    lohi = pb - pa
    u = pa + rng.random(mu.shape) * lohi
    u = np.clip(u, 1e-12, 1 - 1e-12)
    out = mu + sd * ndtri(u)
    # if the interval is numerically empty (deep tail) fall back to the midpoint
    bad = (lohi <= 1e-12) | ~np.isfinite(out)
    if bad.any():
        mid = np.where(np.isfinite(a) & np.isfinite(b), (a + b) / 2,
                       np.where(np.isfinite(b), b, a))
        out = np.where(bad, mid, out)
    return np.clip(out, a, b)


def run_chain(seed):
    rng = np.random.default_rng(seed)
    # --- init
    theta = rng.normal(0, 0.5, (I, T))
    alpha = np.abs(rng.normal(1, 0.2, J)) + 0.5
    beta = rng.normal(0, 0.5, J)
    sig2 = np.full(J, 1.0)
    om2 = 0.05
    z = np.where(kind == 0, lo, np.where(kind == 1, (lo + hi) / 2, hi - 0.5))

    keep_theta, keep_par = [], []
    t0 = time.time()
    for it in range(N_ITER):
        a_o, b_o, s_o = alpha[oj], beta[oj], np.sqrt(sig2[oj])
        mu = b_o + a_o * theta[oi, ot]

        # ---- 1. latent z for censored / banded observations
        m = kind > 0
        z[m] = rtruncnorm(mu[m], s_o[m], lo[m], hi[m], rng)

        # ---- 2. theta | z  (FFBS, vectorised over institutions)
        prec_o = a_o ** 2 / sig2[oj]
        num_o = a_o * (z - b_o) / sig2[oj]
        P = np.bincount(cell, weights=prec_o, minlength=I * T).reshape(I, T)
        Ybar = np.zeros((I, T))
        S = np.bincount(cell, weights=num_o, minlength=I * T).reshape(I, T)
        nz = P > 0
        Ybar[nz] = S[nz] / P[nz]

        mflt = np.empty((I, T)); Cflt = np.empty((I, T))
        a_t = np.zeros(I); R_t = np.full(I, TAU0 ** 2)
        for t in range(T):
            if t > 0:
                a_t = mflt[:, t - 1]
                R_t = Cflt[:, t - 1] + om2
            Pt = P[:, t]
            C = 1.0 / (1.0 / R_t + Pt)
            mflt[:, t] = C * (a_t / R_t + Pt * Ybar[:, t])
            Cflt[:, t] = C
        theta[:, T - 1] = mflt[:, T - 1] + np.sqrt(Cflt[:, T - 1]) * rng.standard_normal(I)
        for t in range(T - 2, -1, -1):
            h = 1.0 / (1.0 / Cflt[:, t] + 1.0 / om2)
            mu_b = h * (mflt[:, t] / Cflt[:, t] + theta[:, t + 1] / om2)
            theta[:, t] = mu_b + np.sqrt(h) * rng.standard_normal(I)

        # ---- 3. alpha, beta | z, theta   (per system)
        th_o = theta[oi, ot]
        for j in range(J):
            s = oj == j
            zz, tt = z[s], th_o[s]
            n = zz.size
            # beta | alpha
            prec = 1.0 / S_BETA ** 2 + n / sig2[j]
            mean = (np.sum(zz - alpha[j] * tt) / sig2[j]) / prec
            beta[j] = mean + rng.standard_normal() / np.sqrt(prec)
            # alpha | beta, truncated positive
            prec = 1.0 / S_ALPHA ** 2 + np.sum(tt ** 2) / sig2[j]
            mean = (A_ALPHA / S_ALPHA ** 2 + np.sum(tt * (zz - beta[j])) / sig2[j]) / prec
            sd = 1.0 / np.sqrt(prec)
            alpha[j] = float(rtruncnorm(np.array([mean]), np.array([sd]),
                                        np.array([1e-4]), np.array([np.inf]), rng)[0])
            # ---- 4. sigma^2
            ssr = float(np.sum((zz - beta[j] - alpha[j] * tt) ** 2))
            sig2[j] = 1.0 / rng.gamma(A_SIG + n / 2.0, 1.0 / (B_SIG + ssr / 2.0))

        # ---- 5. omega^2
        dif = np.diff(theta, axis=1)
        om2 = 1.0 / rng.gamma(A_OM + dif.size / 2.0,
                              1.0 / (B_OM + float(np.sum(dif ** 2)) / 2.0))

        if it >= BURN and (it - BURN) % THIN == 0:
            keep_theta.append(theta.astype(np.float32).copy())
            keep_par.append(np.concatenate([alpha, beta, np.sqrt(sig2), [np.sqrt(om2)]]))
        if it % 500 == 0:
            print(f"  chain {seed} iter {it:5d}  omega={np.sqrt(om2):.3f} "
                  f"alpha={np.round(alpha,2)}  [{time.time()-t0:.0f}s]", flush=True)
    return np.array(keep_theta), np.array(keep_par)


def combine():
    """Stitch per-chain files into posterior.npz, checking they agree on shape."""
    import glob as _g
    fs = sorted(_g.glob(f"{W}/posterior_chain*.npz"))
    if len(fs) < 2:
        raise SystemExit(f"only {len(fs)} chain files found; need at least 2")
    TH, PAR = [], []
    for f in fs:
        z = np.load(f, allow_pickle=True)
        if int(z["I"]) != I or int(z["J"]) != J:
            raise SystemExit(f"{f} was fit on I={int(z['I'])}, J={int(z['J'])}, "
                             f"but model_data.npz now has I={I}, J={J}. Refit.")
        TH.append(z["theta"]); PAR.append(z["par"])
    n = min(t.shape[0] for t in TH)
    TH = np.stack([t[-n:] for t in TH]); PAR = np.stack([p[-n:] for p in PAR])
    np.savez_compressed(f"{W}/posterior.npz", theta=TH, par=PAR,
                        systems=systems, years=years)
    print(f"combined {len(fs)} chains -> posterior.npz {TH.shape}")


if __name__ == "__main__":
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if arg == "combine":
        combine()
    elif arg is not None:
        # one chain per invocation, saved immediately: a killed run costs one
        # chain, not the whole fit
        c = int(arg)
        print(f"=== chain {c} ({N_ITER} iterations)")
        th, pa = run_chain(1000 + c)
        np.savez_compressed(f"{W}/posterior_chain{c}.npz", theta=th, par=pa,
                            systems=systems, years=years, I=I, T=T, J=J)
        print(f"saved chain {c}: {th.shape}")
    else:
        TH, PAR = [], []
        for c in range(CHAINS):
            print(f"=== chain {c}")
            th, pa = run_chain(1000 + c)
            TH.append(th); PAR.append(pa)
        np.savez_compressed(f"{W}/posterior.npz", theta=np.stack(TH),
                            par=np.stack(PAR), systems=systems, years=years)
        print("saved")
