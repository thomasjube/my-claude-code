"""Compression exacte du gaspillage (CP-SAT) : ré-affecte les datasets d'un sous-ensemble de groupes
d'un même type pour minimiser le volume utilisé, sans changer les modèles entraînés ni les sources.

Usage : squeeze.py <instance.json> <solution.json> <sortie.json> [time=s] [k=n] [sub=s] [seed=n] [workers=n]

Groupes = (modèle, type) pour les cibles non sourcées sur ce type et les sources. Les groupes de
modèles « pleins » ne reçoivent que des datasets libres. Les datasets libérés restent disponibles
pour une insertion ultérieure (solveur C++ avec init=).
"""
import sys, json, random, time
from ortools.sat.python import cp_model

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
TLIM = float(args.get("time", 300)); K = int(args.get("k", 60)); SUB = float(args.get("sub", 10))
WORKERS = int(args.get("workers", 4)); rng = random.Random(int(args.get("seed", 1)))
inst = json.load(open(sys.argv[1])); sol = json.load(open(sys.argv[2])); OUT = sys.argv[3]
M, D = inst["models"], inst["datasets"]
req = [{TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()} for m in M]
dT = [TYPES.index(d["dataType"]) for d in D]; dS = [d["size"] for d in D]; dC = [d["isCopyrighted"] for d in D]
owner = [None] * len(D); data_of = {}
for d, m in sol["dataMappings"]:
    owner[d] = m; data_of.setdefault(m, []).append(d)
sources = {s for s, _ in sol["modelMappings"]}
sourced_t = {}
for s, t in sol["modelMappings"]:
    sourced_t.setdefault(t, set()).add(next(iter(req[s])))
full = {m for m in data_of if m not in sources and m not in sourced_t and all(not dC[d] for d in data_of[m])}
groups = {t: [] for t in range(4)}
for m, ds in data_of.items():
    for t in {dT[d] for d in ds}:
        groups[t].append(m)


def waste(t, m):
    return sum(dS[d] for d in data_of[m] if dT[d] == t) - req[m][t][0]


tot = sum(waste(t, m) for t in range(4) for m in groups[t])
print(f"gaspillage initial {tot}", file=sys.stderr, flush=True)
t0 = time.time(); it = 0
while time.time() - t0 < TLIM:
    it += 1
    t = rng.randrange(4)
    gs = groups[t]
    ws = sorted(gs, key=lambda m: -waste(t, m))
    sel = set(ws[:K // 2]) | set(rng.sample(gs, min(K // 2, len(gs))))
    sel = list(sel)
    pool = [d for d in range(len(D)) if dT[d] == t and (owner[d] is None or owner[d] in sel)]
    old = sum(dS[d] for d in pool if owner[d] is not None)
    md = cp_model.CpModel(); X = {}; byd = {}
    for m in sel:
        L, U = req[m][t]
        terms = []
        for d in pool:
            if dS[d] <= U and not (m in full and dC[d]):
                v = md.NewBoolVar(""); X[d, m] = v; terms.append(dS[d] * v); byd.setdefault(d, []).append(v)
                md.AddHint(v, 1 if owner[d] == m else 0)
        md.Add(sum(terms) >= L); md.Add(sum(terms) <= U)
    for vs in byd.values():
        if len(vs) > 1: md.AddAtMostOne(vs)
    obj = sum(dS[d] * v for (d, m), v in X.items())
    md.Add(obj <= old)
    md.Minimize(obj)
    so = cp_model.CpSolver(); so.parameters.max_time_in_seconds = SUB; so.parameters.num_workers = WORKERS
    st = so.Solve(md)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE) or so.ObjectiveValue() >= old:
        continue
    for m in sel:
        data_of[m] = [d for d in data_of[m] if dT[d] != t]
    for d in pool:
        owner[d] = None
    for (d, m), v in X.items():
        if so.Value(v):
            owner[d] = m; data_of[m].append(d)
    tot -= old - int(so.ObjectiveValue())
    print(f"[{time.time() - t0:.0f}s] it {it} type {t} : -{old - int(so.ObjectiveValue())} -> gaspillage {tot}",
          file=sys.stderr, flush=True)
json.dump({"dataMappings": [[d, m] for d, m in enumerate(owner) if m is not None],
           "modelMappings": sol["modelMappings"]}, open(OUT, "w"))
print(f"fin : gaspillage {tot}, libres {sum(1 for o in owner if o is None)}", file=sys.stderr)
