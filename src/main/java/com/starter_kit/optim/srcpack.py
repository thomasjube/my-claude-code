"""Remplissage exact des sources d'un plan (instance 6), type par type, par CP-SAT.

Usage : srcpack.py <instance.json> <plan.txt> <sortie.txt> [time=s par type] [alt=n] [workers=n] [free=0/1]

Par type t : n_t = nombre de sources prévues. Datasets : non libres de type t (et libres si free=1).
Candidats : sources prévues + `alt` modèles à besoin unique non prévus (petite borne basse d'abord).
Objectif : maximiser le nombre de sources remplies (au plus n_t), puis préférer les sources prévues, puis
minimiser le volume consommé. Sortie : lignes « S modèle d1 d2 ... » (option preSrcFile= du solveur).
"""
import sys, json
from ortools.sat.python import cp_model

TYPES = "ntic"
inst = json.load(open(sys.argv[1])); OUT = sys.argv[3]
args = dict(a.split("=", 1) for a in sys.argv[4:])
M, D = inst["models"], inst["datasets"]
T = float(args.get("time", 120)); ALT = int(args.get("alt", 150)); W = int(args.get("workers", 3))
planned_any, PS = set(), []
for l in open(sys.argv[2]):
    p = l.split(); m = int(p[0])
    if float(p[1]) > .5 or float(p[2]) > .5: planned_any.add(m)
    if float(p[3]) > .5: PS.append(m)
own = {}
if args.get("hint"):
    hs = json.load(open(args["hint"]))
    hsrc = {a for a, _ in hs["modelMappings"]}
    own = {d: m for d, m in hs["dataMappings"] if m in hsrc}
out = open(OUT, "w")
for t in range(4):
    tt = TYPES[t]
    ps = [m for m in PS if tt in M[m]["dataRequirements"]]
    n_t = len(ps)
    alts = sorted((i for i, m in enumerate(M) if len(m["dataRequirements"]) == 1 and tt in m["dataRequirements"]
                   and i not in planned_any and i not in ps
                   and m["dataRequirements"][tt]["upperBound"] >= m["dataRequirements"][tt]["lowerBound"]),
                  key=lambda i: (M[i]["dataRequirements"][tt]["lowerBound"], M[i]["energyCost"]))[:ALT]
    cands = ps + alts
    cands += [m for m in set(own.values()) if tt in M[m]["dataRequirements"] and m not in cands]
    ds = [i for i, d in enumerate(D) if d["dataType"] == tt and (d["isCopyrighted"] or args.get("free") == "1")]
    md = cp_model.CpModel(); Y = {}; X = {}; byd = {}
    for m in cands:
        L, U = M[m]["dataRequirements"][tt]["lowerBound"], M[m]["dataRequirements"][tt]["upperBound"]
        y = md.NewBoolVar(""); Y[m] = y; terms = []
        for d in ds:
            if D[d]["size"] <= U:
                v = md.NewBoolVar(""); X[d, m] = v; terms.append(D[d]["size"] * v); byd.setdefault(d, []).append(v)
        if not terms: md.Add(y == 0); continue
        md.Add(sum(terms) >= L * y); md.Add(sum(terms) <= U * y)
    for vs in byd.values():
        if len(vs) > 1: md.AddAtMostOne(vs)
    md.Add(sum(Y.values()) <= n_t)
    vol = sum(D[d]["size"] * v for (d, m), v in X.items())
    emax = sorted(M[m]["energyCost"] for m in ps)[len(ps) // 2] if ps else 0
    for m in alts:
        if M[m]["energyCost"] > emax and m in Y: md.Add(Y[m] == 0)
    esc = max(1, emax // 10**5)
    md.Maximize(10**12 * sum(Y.values()) + 10**9 * sum(Y[m] for m in ps)
                - sum((M[m]["energyCost"] // esc) * Y[m] for m in cands) * 10**3 - vol)
    if own:
        hm = set(own.values())
        for m in cands: md.AddHint(Y[m], 1 if m in hm else 0)
        for (d, m), v in X.items(): md.AddHint(v, 1 if own.get(d) == m else 0)
    so = cp_model.CpSolver(); so.parameters.max_time_in_seconds = T; so.parameters.num_workers = W
    st = so.Solve(md)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"type {t}: pas de solution", file=sys.stderr); continue
    got = [m for m in cands if so.Value(Y[m])]
    for m in got:
        out.write("S %d %s\n" % (m, " ".join(str(d) for d in ds if (d, m) in X and so.Value(X[d, m]))))
    print(f"type {t}: prévues {n_t}, remplies {len(got)} (dont prévues {sum(1 for m in got if m in ps)}), "
          f"variables {len(X)}, {so.StatusName(st)}", file=sys.stderr, flush=True)
out.close()
