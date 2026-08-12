"""06_figures.py -- static figures for the methods memo."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

W = os.path.expanduser("~/uniranks/work")
FIG = f"{W}/figures"; os.makedirs(FIG, exist_ok=True)

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300",
          "#4a3aa7", "#e34948"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#256abf",
       "#184f95", "#0d366b"]
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
SURF = "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": "#d9d8d2", "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "grid.color": "#ececE6", "grid.linewidth": 0.8,
})

sc = pd.read_csv(f"{W}/latent_scores.csv")
item = pd.read_csv(f"{W}/item_parameters.csv")
ed = pd.read_csv(f"{W}/edition_summary.csv")


def finish(ax, title, sub=None, ylab=None):
    fig = ax.figure
    fig.text(.012, .975, title, fontsize=13, fontweight="600", color=INK, va="top")
    if sub:
        fig.text(.012, .928, sub, fontsize=9.3, color=INK2, va="top")
    if ylab:
        ax.set_ylabel(ylab, fontsize=9.5)
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)


# ---------------------------------------------------------------- 1 trajectories
picks = ["Tsinghua University", "National University of Singapore",
         "University of Oxford", "Harvard University",
         "University of Melbourne", "Peking University"]
fig, ax = plt.subplots(figsize=(9.5, 5.4))
for k, nm in enumerate(picks):
    g = sc[(sc.inst_name == nm)].sort_values("year")
    g = g[(g.year >= 2004) & (g.year <= 2025)]
    if g.empty:
        continue
    ax.fill_between(g.year, g.theta_q05, g.theta_q95, color=SERIES[k], alpha=.13, lw=0)
    ax.plot(g.year, g.theta_mean, color=SERIES[k], lw=2, zorder=3)
    ax.annotate(nm, (g.year.iloc[-1], g.theta_mean.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", color=SERIES[k], fontsize=9,
                fontweight="600", va="center")
ax.set_xlim(2004, 2032.5)
finish(ax, "Latent quality trajectories, 2004-2025",
       "Posterior mean with 90% credible band, pooled across 12 ranking systems", "latent quality (theta)")
fig.tight_layout(rect=[0, 0, 1, .90]); fig.savefig(f"{FIG}/fig1_trajectories.png", dpi=170); plt.close(fig)

# ---------------------------------------------------------------- 2 reliability
it = item.sort_values("reliability")
fig, ax = plt.subplots(figsize=(8.4, 4.6))
y = np.arange(len(it))
ax.barh(y, it.reliability, color=SEQ[4], height=.6, zorder=3)
ax.hlines(y, it.reliability_lo, it.reliability_hi, color=SEQ[6], lw=2, zorder=4)
for k, (v, s) in enumerate(zip(it.reliability, it.system)):
    ax.text(v + .015, k, f"{v:.2f}", va="center", fontsize=9, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(it.system)
ax.set_xlim(0, 1.02); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
finish(ax, "How much of each ranking is the common factor?",
       "alpha^2/(alpha^2+sigma^2) with 95% credible interval; 1.0 = the shared dimension explains everything")
fig.tight_layout(rect=[0, 0, 1, .90]); fig.savefig(f"{FIG}/fig2_reliability.png", dpi=170); plt.close(fig)

# ---------------------------------------------------------------- 3 coverage
piv = ed.pivot_table(index="system", columns="ref_year", values="N")
order = ed.groupby("system")["ref_year"].min().sort_values().index
piv = piv.reindex(order)
fig, ax = plt.subplots(figsize=(11, 4.2))
cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", SEQ)
im = ax.imshow(np.log10(piv.values), aspect="auto", cmap=cmap,
               vmin=np.log10(80), vmax=np.log10(3200))
ax.set_xticks(range(len(piv.columns)), piv.columns, rotation=90, fontsize=8)
ax.set_yticks(range(len(piv.index)), piv.index, fontsize=9)
for a in range(piv.shape[0]):
    for b in range(piv.shape[1]):
        v = piv.values[a, b]
        if not np.isnan(v):
            ax.text(b, a, f"{int(v)}", ha="center", va="center", fontsize=6.2,
                    color="white" if np.log10(v) > np.log10(700) else INK)
fig.text(.012, .975, "Which ranking published how many institutions, in which year",
         fontsize=13, fontweight="600", color=INK, va="top")
fig.text(.012, .928, "Blank = no edition reachable. Reference year; THE, U.S. News and post-2013 QS editions shifted back one year.",
         fontsize=9.3, color=INK2, va="top")
ax.grid(visible=False)
fig.tight_layout(rect=[0, 0, 1, .90]); fig.savefig(f"{FIG}/fig3_coverage.png", dpi=170); plt.close(fig)

# ---------------------------------------------------------------- 4 country share of top 200
top = sc[sc.in_sample].copy()
top["r"] = top.groupby("year")["theta_mean"].rank(ascending=False)
t200 = top[top.r <= 200]
cc = (t200.groupby(["year", "country"]).size().rename("n").reset_index())
big = cc.groupby("country")["n"].sum().sort_values(ascending=False).head(6).index
fig, ax = plt.subplots(figsize=(9.5, 5.2))
for k, c in enumerate(big):
    g = cc[(cc.country == c) & (cc.year >= 2004) & (cc.year <= 2025)].sort_values("year")
    ax.plot(g.year, g.n, color=SERIES[k], lw=2, marker="o", ms=3.5, zorder=3)
    ax.annotate(c, (g.year.iloc[-1], g.n.iloc[-1]), xytext=(6, 0), textcoords="offset points",
                color=SERIES[k], fontsize=9, fontweight="600", va="center")
ax.set_xlim(2004, 2031)
finish(ax, "Institutions in the global top 200 on the latent scale",
       "Counted from the pooled estimate, not from any single published table", "institutions")
fig.tight_layout(rect=[0, 0, 1, .90]); fig.savefig(f"{FIG}/fig4_countries.png", dpi=170); plt.close(fig)

# ---------------------------------------------------------------- 5 risers/fallers
a, b = 2006, 2024
obs = sc[sc.in_sample]
elig = (set(obs[obs.year.between(a - 1, a + 2)].inst_id)
        & set(obs[obs.year.between(b - 2, b + 1)].inst_id))
win = obs[obs.year.between(a, b)]
dense = win.groupby("inst_id")["year"].nunique()
thick = win.groupby("inst_id")["n_listings"].mean()
elig &= set(dense[dense >= 12].index) & set(thick[thick >= 1.5].index)
wide = sc[sc.year.isin([a, b])].pivot_table(index=["inst_id", "inst_name", "country"],
                                            columns="year", values="theta_z_withinyear")
wide = wide[wide.index.get_level_values(0).isin(elig)].dropna()
wide["chg"] = wide[b] - wide[a]
sel = pd.concat([wide.nlargest(10, "chg"), wide.nsmallest(10, "chg")]).sort_values("chg")
fig, ax = plt.subplots(figsize=(9.2, 6.4))
lbl = [f"{n}  ({c})" for _, n, c in sel.index]
col = [SERIES[2] if v > 0 else SERIES[7] for v in sel.chg]
ax.barh(np.arange(len(sel)), sel.chg, color=col, height=.62, zorder=3)
ax.set_yticks(np.arange(len(sel)), lbl, fontsize=8.5)
ax.axvline(0, color=MUTED, lw=1)
ax.grid(axis="x"); ax.grid(axis="y", visible=False)
finish(ax, f"Largest changes in relative standing, {a} to {b}",
       "Change in within-year standardised latent quality; institutions listed near both endpoints and in >= 12 intervening years")
ax.legend(handles=[Patch(color=SERIES[2], label="rose"), Patch(color=SERIES[7], label="fell")],
          frameon=False, fontsize=9, loc="lower right")
fig.tight_layout(rect=[0, 0, 1, .90]); fig.savefig(f"{FIG}/fig5_movers.png", dpi=170); plt.close(fig)

# ---------------------------------------------------------------- 6 uncertainty
fig, ax = plt.subplots(figsize=(8.6, 4.6))
g = sc[sc.in_sample].groupby("n_listings")["theta_sd"].agg(["mean", "size"]).reset_index()
g = g[g["size"] >= 30]
ax.bar(g.n_listings, g["mean"], color=SEQ[4], width=.62, zorder=3)
for _, r in g.iterrows():
    ax.text(r.n_listings, r["mean"] + .004, f"{r['mean']:.2f}\nn={int(r['size']):,}",
            ha="center", fontsize=8, color=INK2)
ax.set_xlabel("number of ranking systems listing the institution that year")
ax.set_ylim(0, g["mean"].max() * 1.28)
finish(ax, "Uncertainty falls as more rankings weigh in",
       "Posterior standard deviation of latent quality", "posterior sd of theta")
fig.tight_layout(rect=[0, 0, 1, .90]); fig.savefig(f"{FIG}/fig6_uncertainty.png", dpi=170); plt.close(fig)

print("figures written to", FIG)
for f in sorted(os.listdir(FIG)):
    print("  ", f)
