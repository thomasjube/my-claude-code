"""Relaxation linéaire (HiGHS) : borne supérieure et plan de guidage pour le solveur C++.

Variables par modèle : x (plein, données libres), y (moitié), s (source, modèles à besoin unique),
a (alias, copie entièrement sourcée), et par besoin des modèles « moitié » : d (données) / z (source).
Les données sont agrégées en volume par type (libres / toutes), sans granularité des datasets.

Usage : lp.py <instance.json> <plan.txt> [alias=0/1] [mip=secondes] [dslack=f] [freeslack=f] [threads=n]
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
freeslack = float(opts.get("freeslack", "0"))
srcmin = int(opts.get("srcmin", "0"))  # consommation minimale = taille du k-ième plus petit dataset du type
M, D, cap = inst["models"], inst["datasets"], inst["energyCap"]
N = len(M)
S = [0.0] * 4; F = [0.0] * 4
for d in D:
    t = TYPES.index(d["dataType"]); S[t] += d["size"]
    if not d["isCopyrighted"]: F[t] += d["size"]
minsz = [0] * 4
if srcmin > 0:
    for t in range(4):
        sizes = sorted(d["size"] for d in D if TYPES.index(d["dataType"]) == t)
        minsz[t] = sizes[min(srcmin, len(sizes)) - 1]
cons = lambda t, l: max(l, minsz[t])
S = [v * (1 - dslack) for v in S]; F = [v * (1 - dslack - freeslack) for v in F]

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
            if i in X: free[X[i]] = cons(t, l) / F[t] if F[t] else 0; tot[X[i]] = tot.get(X[i], 0) + cons(t, l) / S[t]
            if (i, k) in Dv: tot[Dv[i, k]] = cons(t, l) / S[t]
            src[Zv[i, k]] = 1.0
            if i in A: src[A[i]] = src.get(A[i], 0) + 1.0
        if i in Sv and TYPES.index(next(iter(m["dataRequirements"]))) == t:
            l = next(iter(m["dataRequirements"].values()))["lowerBound"]
            tot[Sv[i]] = cons(t, l) / S[t]; src[Sv[i]] = -1.0
    if F[t]: rows.append((-inf, 1.0, free))
    else:  # aucune donnée libre : pas de modèle plein utilisant ce type
        for c in free: rows.append((-inf, 0.0, {c: 1.0}))
    rows.append((-inf, 1.0, tot))
    rows.append((-inf, 0.0, src))               # besoins sourcés <= sources disponibles

if opts.get("vk", "0") in ("1", "2"):
    # coupes convexes nombre/volume : n groupes consomment au moins les n plus petits datasets, d'où pour tout k
    # somme_g max(L_g, s_k) <= V_tot - V(k) + k s_k  (s trié croissant, V(k) = somme des k plus petits)
    nvk = 0
    for t in range(4):
        for sub in ("all", "free"):
            sz = sorted(d["size"] for d in D if TYPES.index(d["dataType"]) == t and (sub == "all" or not d["isCopyrighted"]))
            if not sz: continue
            Vt = sum(sz) * (1 - dslack - (freeslack if sub == "free" else 0))
            pref = [0]
            for v in sz: pref.append(pref[-1] + v)
            # vk=2 : un groupe de borne L utilise au moins nmin(L) datasets (les plus gros atteignent L)
            import bisect
            desc = [0]
            for v in reversed(sz): desc.append(desc[-1] + v)
            nmin = (lambda l: max(1, bisect.bisect_left(desc, l))) if opts.get("vk") == "2" else (lambda l: 1)
            ks = sorted({k for k in [1, 2, 3, 5, 8, 12, 20, 30, 50, 80, 120, 200, 300, 500, 800, 1200, 2000, 3000, 5000, 8000, 12000, 20000] if k <= len(sz)})
            for k in ks:
                sk = sz[k - 1]; rhs = Vt - pref[k] + k * sk
                row = {}
                for i, m in enumerate(M):
                    rq = [(TYPES.index(tt), r["lowerBound"], r["upperBound"]) for tt, r in m["dataRequirements"].items()]
                    for kk, (tt, l, u) in enumerate(rq):
                        if tt != t: continue
                        c = float(max(l, nmin(l) * sk))
                        if i in X: row[X[i]] = row.get(X[i], 0) + c
                        if sub == "all" and (i, kk) in Dv: row[Dv[i, kk]] = c
                    if sub == "all" and i in Sv and len(rq) == 1 and rq[0][0] == t:
                        row[Sv[i]] = float(max(rq[0][1], nmin(rq[0][1]) * sk))
                if row:
                    sc = 1.0 / rhs
                    rows.append((-inf, 1.0, {c: v * sc for c, v in row.items()})); nvk += 1
    print(f"coupes nombre/volume : {nvk}", file=sys.stderr)
if opts.get("count", "0") == "1":
    # nombre de datasets : un groupe de borne basse L utilise au moins nmin(L) datasets
    # (plus petit k tel que les k plus gros datasets atteignent L)
    import bisect
    for t in range(4):
        cnt = {}
        for sub, cond in (("all", lambda d: True), ("free", lambda d: not d["isCopyrighted"])):
            sz = sorted((d["size"] for d in D if TYPES.index(d["dataType"]) == t and cond(d)), reverse=True)
            pref = [0]
            for v in sz: pref.append(pref[-1] + v)
            nmin = lambda l: max(1, bisect.bisect_left(pref, l))
            row = {}
            for i, m in enumerate(M):
                rq = [(TYPES.index(tt), r["lowerBound"], r["upperBound"]) for tt, r in m["dataRequirements"].items()]
                for k, (tt, l, u) in enumerate(rq):
                    if tt != t: continue
                    if i in X: row[X[i]] = row.get(X[i], 0) + nmin(l)
                    if sub == "all" and (i, k) in Dv: row[Dv[i, k]] = float(nmin(l))
                if sub == "all" and i in Sv and len(rq) == 1 and rq[0][0] == t:
                    row[Sv[i]] = float(nmin(rq[0][1]))
            if row: rows.append((-inf, float(len(sz)), row))
if opts.get("hall", "0") == "1":
    # contraintes de Hall : un groupe de borne haute U ne peut utiliser que des datasets de taille <= U
    nth = int(opts.get("hallk", "60"))
    nh = 0
    for t in range(4):
        sizes_all = sorted(d["size"] for d in D if TYPES.index(d["dataType"]) == t)
        sizes_free = sorted(d["size"] for d in D if TYPES.index(d["dataType"]) == t and not d["isCopyrighted"])
        qs = sorted({sizes_all[min(len(sizes_all) - 1, int(len(sizes_all) * q / nth))] for q in range(1, nth)})
        import bisect
        for b in qs:
            ca = bisect.bisect_right(sizes_all, b); va = sum(sizes_all[:ca])
            cf = bisect.bisect_right(sizes_free, b); vf = sum(sizes_free[:cf])
            cnt_all, vol_all, cnt_free, vol_free = {}, {}, {}, {}
            for i, m in enumerate(M):
                rq = [(TYPES.index(tt), r["lowerBound"], r["upperBound"]) for tt, r in m["dataRequirements"].items()]
                for k, (tt, l, u) in enumerate(rq):
                    if tt != t or u > b or u < l:
                        continue
                    if i in X:
                        cnt_all[X[i]] = cnt_all.get(X[i], 0) + 1; vol_all[X[i]] = vol_all.get(X[i], 0) + l
                        cnt_free[X[i]] = cnt_free.get(X[i], 0) + 1; vol_free[X[i]] = vol_free.get(X[i], 0) + l
                    if (i, k) in Dv:
                        cnt_all[Dv[i, k]] = 1.0; vol_all[Dv[i, k]] = float(l)
                if i in Sv and len(rq) == 1 and rq[0][0] == t and rq[0][2] <= b:
                    cnt_all[Sv[i]] = 1.0; vol_all[Sv[i]] = float(rq[0][1])
            if cnt_all:
                rows.append((-inf, float(ca), cnt_all)); rows.append((-inf, float(va), vol_all)); nh += 2
            if cnt_free:
                rows.append((-inf, float(cf), cnt_free)); rows.append((-inf, float(vf), vol_free)); nh += 2
    print(f"contraintes de Hall : {nh}", file=sys.stderr)
if opts.get("forbid"):
    # modèles interdits en « plein » (échecs de réalisation observés)
    nfb = 0
    for line in open(opts["forbid"]):
        for tok in line.split():
            i = int(tok)
            if i in X:
                cols_ub[X[i]] = 0.0; nfb += 1
    print(f"pleins interdits : {nfb}", file=sys.stderr)
if float(opts.get("noise", "0")) > 0:
    # bruit sur les valeurs : plans différents de valeur quasi égale (diversification)
    import random as _r
    _rng = _r.Random(int(opts.get("seed", "1")))
    eps = float(opts["noise"])
    cols_cost = [c * (1 + eps * _rng.random()) if c != 0 else c for c in cols_cost]
nc = len(cols_cost)
h.addVars(nc, np.array(cols_lb), np.array(cols_ub))
h.changeColsCost(nc, np.arange(nc, dtype=np.int32), np.array(cols_cost))
for lo, hi, row in rows:
    idx = np.array(list(row.keys()), dtype=np.int32); val = np.array(list(row.values()), dtype=float)
    h.addRow(lo, hi, len(idx), idx, val)
if mip_time > 0:
    h.changeColsIntegrality(nc, np.arange(nc, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * nc))
    h.setOptionValue("time_limit", mip_time)
    h.setOptionValue("mip_rel_gap", float(opts.get("gap", "1e-5")))
    h.setOptionValue("threads", int(opts.get("threads", "1")))
h.run()
fixmip = float(opts.get("fixmip", "0"))
if fixmip > 0 and mip_time == 0:
    # relaxer puis fixer : on fige les variables déjà entières du LP, MILP sur les fractionnaires
    lpsol = list(h.getSolution().col_value)
    lpdual = list(h.getSolution().col_dual)
    tau = float(opts.get("rctau", "inf"))
    nfix = 0
    for j, v in enumerate(lpsol):
        if abs(v - 1) < 1e-7 or (opts.get("fixzero", "0") == "1" and abs(v) < 1e-7) or \
                (abs(v) < 1e-7 and lpdual[j] > tau):
            h.changeColBounds(j, float(round(v)), float(round(v)))
            nfix += 1
    print(f"LP {-h.getInfo().objective_function_value:.1f}, variables figées {nfix}/{nc}", file=sys.stderr)
    h.changeColsIntegrality(nc, np.arange(nc, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * nc))
    h.setOptionValue("time_limit", fixmip)
    h.setOptionValue("mip_rel_gap", float(opts.get("gap", "0")))
    h.run()
    mip_time = fixmip
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
