"""Vérifie exactement (HiGHS) la faisabilité, type par type, du remplissage libre de tous les pleins d'un plan.

Usage : ptcheck.py <instance.json> <plan.txt> [time=s] [relaxU=1]
"""
import sys, json
import numpy as np
import highspy

TYPES = "ntic"
inst = json.load(open(sys.argv[1])); args = dict(a.split("=", 1) for a in sys.argv[3:])
M, D = inst["models"], inst["datasets"]
X = [int(l.split()[0]) for l in open(sys.argv[2]) if float(l.split()[1]) > 0.5]
for t in range(4):
    gs = [(m, M[m]["dataRequirements"][TYPES[t]]) for m in X if TYPES[t] in M[m]["dataRequirements"]]
    ds = [i for i, d in enumerate(D) if d["dataType"] == TYPES[t] and not d["isCopyrighted"]]
    h = highspy.Highs(); h.setOptionValue("output_flag", False); h.setOptionValue("time_limit", float(args.get("time", 120)))
    V = {}; n = 0
    for gi, (m, r) in enumerate(gs):
        U = r["upperBound"] if args.get("relaxU") != "1" else 10**9
        for d in ds:
            if D[d]["size"] <= U: V[d, gi] = n; n += 1
    h.addVars(n, np.zeros(n), np.ones(n))
    h.changeColsIntegrality(n, np.arange(n, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * n))
    cost = np.zeros(n)
    for (d, gi), v in V.items(): cost[v] = D[d]["size"]
    h.changeColsCost(n, np.arange(n, dtype=np.int32), cost)
    for gi, (m, r) in enumerate(gs):
        idx = [V[d, gi] for d in ds if (d, gi) in V]
        U = r["upperBound"] if args.get("relaxU") != "1" else 1e12
        h.addRow(r["lowerBound"], U, len(idx), np.array(idx, dtype=np.int32), np.array([float(D[d]["size"]) for d in ds if (d, gi) in V]))
    byd = {}
    for (d, gi), v in V.items(): byd.setdefault(d, []).append(v)
    for d, vs in byd.items():
        h.addRow(-highspy.kHighsInf, 1, len(vs), np.array(vs, dtype=np.int32), np.ones(len(vs)))
    h.run()
    print(f"type {t}: groupes {len(gs)}, datasets libres {len(ds)}, besoin {sum(r['lowerBound'] for _, r in gs)}, "
          f"volume {sum(D[d]['size'] for d in ds)} -> {h.modelStatusToString(h.getModelStatus())}", flush=True)
