"""Relaxation linéaire (HiGHS) : borne supérieure et plan de guidage pour le solveur C++.

Variables par modèle : x (plein, données libres), y (moitié), s (source, modèles à besoin unique),
a (alias, copie entièrement sourcée), et par besoin des modèles « moitié » : d (données) / z (source).
Les données sont agrégées en volume par type (libres / toutes), sans granularité des datasets.

Usage : lp.py <instance.json> <plan.txt> [alias=0/1] [mip=secondes] [dslack=f]
Le plan contient une ligne par modèle : id x y s a z_1 .. z_k (z = besoin sourcé, ordre des besoins)
dslack réduit les volumes de données disponibles (marge pour la granularité des datasets).
"""
import sys, json
import numpy as np
import highspy

TYPES = "ntic"
inst = json.load(open(sys.argv[1]))
out = sys.argv[2]
opts = dict(a.split("=") for a in sys.argv[3:])
use_alias = opts.get("alias", "0") == "1"
mip_time = float(opts.get("mip", "0"))
dslack = float(opts.get("dslack", "0"))
M, D, cap = inst["models"], inst["datasets"], inst["energyCap"]
N = len(M)
S = [0.0] * 4; F = [0.0] * 4
for d in D:
    t = TYPES.index(d["dataType"]); S[t] += d["size"]
    if not d["isCopyrighted"]: F[t] += d["size"]
S = [v * (1 - dslack) for v in S]; F = [v * (1 - dslack) for v in F]

h = highspy.Highs(); h.setOptionValue("output_flag", False)
inf = highspy.kHighsInf
cols_cost, cols_lb, cols_ub = [], [], []
def var(c, ub=1.0):
    cols_cost.append(-c); cols_lb.append(0.0); cols_ub.append(ub); return len(cols_cost) - 1
rows = []  # (lo, hi, {col: coef})
X, Y, Sv, A = {}, {}, {}, {}
Dv, Zv = {}, {}
Escale = cap
for i, m in enumerate(M):
    reqs = [(TYPES.index(t), r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()]
    feas_all = all(u >= l for _, l, u in reqs)
    if feas_all: X[i] = var(m["value"])
    Y[i] = var(m["value"] // 2)
    if len(reqs) == 1 and feas_all: Sv[i] = var(0.0)
    if use_alias: A[i] = var(m["value"] // 2)
    for k, (t, l, u) in enumerate(reqs):
        if u >= l: Dv[i, k] = var(0.0)
        Zv[i, k] = var(0.0)
        row = {Y[i]: -1.0, Zv[i, k]: 1.0}
        if (i, k) in Dv: row[Dv[i, k]] = 1.0
        rows.append((0.0, 0.0, row))           # d + z = y
    row = {Y[i]: 1.0}
    if i in X: row[X[i]] = 1.0
    if i in Sv: row[Sv[i]] = 1.0
    rows.append((-inf, 1.0, row))               # un seul rôle par modèle
# énergie
row = {}
for i, m in enumerate(M):
    e = m["energyCost"] / Escale
    for dct in (X, Y, Sv, A):
        if i in dct: row[dct[i]] = e
rows.append((-inf, 1.0, row))
for t in range(4):
    free, tot, src = {}, {}, {}
    for i, m in enumerate(M):
        reqs = [(TYPES.index(tt), r["lowerBound"], r["upperBound"]) for tt, r in m["dataRequirements"].items()]
        for k, (tt, l, u) in enumerate(reqs):
            if tt != t: continue
            if i in X: free[X[i]] = l / F[t] if F[t] else 0; tot[X[i]] = tot.get(X[i], 0) + l / S[t]
            if (i, k) in Dv: tot[Dv[i, k]] = l / S[t]
            src[Zv[i, k]] = 1.0
            if i in A: src[A[i]] = src.get(A[i], 0) + 1.0
        if i in Sv and TYPES.index(next(iter(m["dataRequirements"]))) == t:
            l = next(iter(m["dataRequirements"].values()))["lowerBound"]
            tot[Sv[i]] = l / S[t]; src[Sv[i]] = -1.0
    if F[t]: rows.append((-inf, 1.0, free))
    else:  # aucune donnée libre : pas de modèle plein utilisant ce type
        for c in free: rows.append((-inf, 0.0, {c: 1.0}))
    rows.append((-inf, 1.0, tot))
    rows.append((-inf, 0.0, src))               # besoins sourcés <= sources disponibles

nc = len(cols_cost)
h.addVars(nc, np.array(cols_lb), np.array(cols_ub))
h.changeColsCost(nc, np.arange(nc, dtype=np.int32), np.array(cols_cost))
for lo, hi, row in rows:
    idx = np.array(list(row.keys()), dtype=np.int32); val = np.array(list(row.values()), dtype=float)
    h.addRow(lo, hi, len(idx), idx, val)
if mip_time > 0:
    h.changeColsIntegrality(nc, np.arange(nc, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * nc))
    h.setOptionValue("time_limit", mip_time)
    h.setOptionValue("mip_rel_gap", 1e-5)
    h.setOptionValue("threads", int(opts.get("threads", "1")))
h.run()
sol = h.getSolution().col_value
bound = -h.getInfo().objective_function_value
info = h.getInfo()
extra = f", borne MIP {-info.mip_dual_bound:.0f}, écart {info.mip_gap:.2e}" if mip_time > 0 else ""
print(f"objectif : {bound:.0f}  (statut {h.modelStatusToString(h.getModelStatus())}{extra})")
nx = sum(sol[c] for c in X.values()); ny = sum(sol[c] for c in Y.values())
ns = sum(sol[c] for c in Sv.values()); na = sum(sol[c] for c in A.values())
print(f"pleins {nx:.0f}, moitié {ny:.0f}, sources {ns:.0f}, alias {na:.0f}")
with open(out, "w") as f:
    for i in range(N):
        g = lambda dct: sol[dct[i]] if i in dct else 0.0
        zs = " ".join(f"{sol[Zv[i, k]]:.4f}" for k in range(len(M[i]["dataRequirements"])))
        f.write(f"{i} {g(X):.4f} {g(Y):.4f} {g(Sv):.4f} {g(A):.4f} {zs}\n")
