"""Faisabilité exacte par type d'un plan (instance 6) : pleins (datasets libres) + sources (quelconques).

Usage : typefeas.py <instance.json> <plan.txt> <type 0-3> <sortie.txt> [time=s] [workers=n] [hint=solution.json]
        [extra=n]  (sources candidates supplémentaires, interchangeables : il faut au moins n_t sources)
Écrit les lignes « D dataset modèle » pour le type traité. Objectif : maximiser le nombre de groupes pleins
satisfaits, toutes les sources requises devant l'être.
"""
import sys, json
from ortools.sat.python import cp_model

TYPES = "ntic"
inst = json.load(open(sys.argv[1])); t = int(sys.argv[3]); OUT = sys.argv[4]
args = dict(a.split("=", 1) for a in sys.argv[5:])
M, D = inst["models"], inst["datasets"]
X, Sr = [], []
for l in open(sys.argv[2]):
    p = l.split(); m = int(p[0])
    if float(p[1]) > .5 and TYPES[t] in M[m]["dataRequirements"]: X.append(m)
    if float(p[3]) > .5 and TYPES[t] in M[m]["dataRequirements"]: Sr.append(m)
need_src = len(Sr)
EXTRA = int(args.get("extra", 0))
if EXTRA:
    planned = set(Sr) | set(X)
    cands = sorted((i for i, m in enumerate(M) if len(m["dataRequirements"]) == 1 and TYPES[t] in m["dataRequirements"]
                    and i not in planned and m["dataRequirements"][TYPES[t]]["upperBound"] >= m["dataRequirements"][TYPES[t]]["lowerBound"]),
                   key=lambda i: M[i]["dataRequirements"][TYPES[t]]["lowerBound"])
    Sr += cands[:EXTRA]
ds = [i for i, d in enumerate(D) if d["dataType"] == TYPES[t]]
sz = {i: D[i]["size"] for i in ds}; cop = {i: D[i]["isCopyrighted"] for i in ds}
md = cp_model.CpModel(); V = {}; byd = {}; Y = {}; Z = {}
for m in X + Sr:
    L, U = M[m]["dataRequirements"][TYPES[t]]["lowerBound"], M[m]["dataRequirements"][TYPES[t]]["upperBound"]
    act = md.NewBoolVar("")
    (Y if m in X else Z)[m] = act
    terms = []
    for d in ds:
        if sz[d] <= U and not (m in X and cop[d]):
            v = md.NewBoolVar(""); V[d, m] = v; terms.append(sz[d] * v); byd.setdefault(d, []).append(v)
    md.Add(sum(terms) >= L * act); md.Add(sum(terms) <= U * act)
for vs in byd.values():
    if len(vs) > 1: md.AddAtMostOne(vs)
md.Add(sum(Z.values()) >= need_src)
md.Maximize(sum(Y.values()))
if args.get("hint"):
    sol = json.load(open(args["hint"]))
    own = {d: m for d, m in sol["dataMappings"]}
    for (d, m), v in V.items(): md.AddHint(v, 1 if own.get(d) == m else 0)
    for m, v in list(Y.items()) + list(Z.items()):
        md.AddHint(v, 1 if any(own.get(d) == m for d in ds) else 0)
print(f"type {t}: pleins {len(X)}, sources {need_src} (+{EXTRA} candidates), datasets {len(ds)}, variables {len(V)}", file=sys.stderr, flush=True)


class CB(cp_model.CpSolverSolutionCallback):
    def on_solution_callback(self):
        print(f"  {self.WallTime():.0f}s pleins satisfaits {self.ObjectiveValue():.0f}/{len(X)} borne {self.BestObjectiveBound():.0f}", file=sys.stderr, flush=True)


so = cp_model.CpSolver(); so.parameters.max_time_in_seconds = float(args.get("time", 300))
so.parameters.num_workers = int(args.get("workers", 4))
st = so.Solve(md, CB())
print(so.StatusName(st), file=sys.stderr)
if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    with open(OUT, "w") as f:
        for (d, m), v in V.items():
            if so.Value(v): f.write(f"D {d} {m}\n")
