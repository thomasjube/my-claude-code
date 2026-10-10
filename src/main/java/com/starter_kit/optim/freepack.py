"""Affectation exacte des datasets libres aux modèles « pleins » d'un plan, type par type (HiGHS).

Usage : freepack.py <instance.json> <plan.txt> <sortie.txt> [time=s par type]

Pour chaque type t : variables x[d,g] (dataset libre d dans le besoin g de type t d'un modèle
plein du plan) et y[g] (besoin satisfait). Contraintes L*y <= somme <= U*y, chaque dataset au plus
une fois. Objectif : maximiser la valeur des besoins satisfaits (valeur du modèle / nb de besoins).
Les modèles dont tous les besoins sont satisfaits sont écrits (lignes « D dataset modèle ») ; le
solveur C++ complète ensuite le reste du plan (option init=).
"""
import sys, json
import numpy as np
import highspy

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
TT = float(args.get("time", 120))
inst = json.load(open(sys.argv[1]))
M, D = inst["models"], inst["datasets"]
full = []
for line in open(sys.argv[2]):
    p = line.split()
    if float(p[1]) > 0.5:
        full.append(int(p[0]))
req = {m: {TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in M[m]["dataRequirements"].items()} for m in full}
ok_groups = {m: 0 for m in full}
assign = {m: [] for m in full}
for t in range(4):
    groups = [m for m in full if t in req[m]]
    ds = [i for i, d in enumerate(D) if not d["isCopyrighted"] and TYPES.index(d["dataType"]) == t]
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("time_limit", TT)
    cost, X, Y = [], {}, {}
    rows = []
    for g, m in enumerate(groups):
        Y[g] = len(cost); cost.append(-M[m]["value"] / len(req[m]))
    for g, m in enumerate(groups):
        L, U = req[m][t]
        row = {}
        for d in ds:
            s = D[d]["size"]
            if s <= U:
                X[d, g] = len(cost); cost.append(1e-6 * s)
                row[X[d, g]] = float(s)
        lo = dict(row); lo[Y[g]] = -float(L)
        hi = dict(row); hi[Y[g]] = -float(U)
        rows.append((0.0, np.inf, lo))
        rows.append((-np.inf, 0.0, hi))
    by_d = {}
    for (d, g), v in X.items():
        by_d.setdefault(d, []).append(v)
    for vs in by_d.values():
        rows.append((-np.inf, 1.0, {v: 1.0 for v in vs}))
    nc = len(cost)
    h.addVars(nc, np.zeros(nc), np.ones(nc))
    h.changeColsCost(nc, np.arange(nc, dtype=np.int32), np.array(cost))
    h.changeColsIntegrality(nc, np.arange(nc, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * nc))
    for lo_, hi_, row in rows:
        ii = np.array(list(row.keys()), dtype=np.int32)
        h.addRow(lo_, hi_, len(ii), ii, np.array(list(row.values())))
    h.run()
    info = h.getInfo()
    x = h.getSolution().col_value if info.primal_solution_status == 2 else None
    nsat = 0
    if x is not None:
        for g, m in enumerate(groups):
            if x[Y[g]] > 0.5:
                nsat += 1
                ok_groups[m] += 1
                assign[m] += [d for d in ds if (d, g) in X and x[X[d, g]] > 0.5]
    print(f"type {t}: {len(groups)} groupes, {len(ds)} datasets libres, {nc} variables, "
          f"satisfaits {nsat} ({h.modelStatusToString(h.getModelStatus())})", file=sys.stderr, flush=True)
done = [m for m in full if ok_groups[m] == len(req[m])]
print(f"modèles pleins réalisés : {len(done)}/{len(full)}", file=sys.stderr)
with open(sys.argv[3], "w") as f:
    for m in done:
        for d in assign[m]:
            f.write(f"D {d} {m}\n")
