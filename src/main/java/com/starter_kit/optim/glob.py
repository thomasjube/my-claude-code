"""Modèle CP-SAT global (instances à données non libres abondantes : 2, 4) amorcé par la meilleure solution.

Usage : glob.py <instance.json> <solution.json> <sortie.json> [time=s] [extra=n] [workers=n] [seed=n]

Variables : f[m] plein (datasets libres, affectation exacte x[d,m]), h[m] moitié (supposée réalisable
en données non libres, vérifiée ensuite par remplissage glouton). Énergie totale <= cap.
Candidats pleins : pleins actuels + `extra` meilleurs rendements ; moitiés : tous les modèles.
Les sources de la solution sont conservées telles quelles (avec leurs cibles).
"""
import sys, json, random, time, bisect
from ortools.sat.python import cp_model

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
TLIM = float(args.get("time", 500)); EXTRA = int(args.get("extra", 100)); WORKERS = int(args.get("workers", 4))
inst = json.load(open(sys.argv[1])); sol = json.load(open(sys.argv[2])); OUT = sys.argv[3]
M, D, CAP = inst["models"], inst["datasets"], inst["energyCap"]
N = len(M)
val = [m["value"] for m in M]; En = [m["energyCost"] for m in M]
req = [{TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()} for m in M]
feasible = [all(U >= L for L, U in r.values()) for r in req]
dT = [TYPES.index(d["dataType"]) for d in D]; dS = [d["size"] for d in D]; dC = [d["isCopyrighted"] for d in D]
owner = [None] * len(D); data_of = {}
for d, m in sol["dataMappings"]:
    owner[d] = m; data_of.setdefault(m, []).append(d)
sources = {s for s, _ in sol["modelMappings"]}
sourced = {t for _, t in sol["modelMappings"]}
fixed = sources | sourced
trained = (set(data_of) | sourced) - sources
full = {m for m in trained if m not in sourced and all(not dC[d] for d in data_of[m])}
half = trained - full - sourced
fixed_val = sum(val[m] // 2 for m in sourced)
fixed_E = sum(En[m] for m in fixed)
# datasets libres réservés aux sources/cibles figées
locked = {d for d in range(len(D)) if owner[d] in fixed}
freeD = [d for d in range(len(D)) if not dC[d] and d not in locked]
has_free = [set() for _ in range(4)]
minL = [sum(L for L, U in r.values()) for r in req]
cand = sorted((m for m in range(N) if feasible[m] and m not in fixed and m not in full),
              key=lambda m: -val[m] / (minL[m] + 1e-9 * En[m]))[:EXTRA]
fulls = sorted(full | set(cand))
md = cp_model.CpModel()
f = {m: md.NewBoolVar("") for m in fulls}
h = {m: md.NewBoolVar("") for m in range(N) if m not in fixed and feasible[m]}
for m in fulls:
    if m in h: md.AddBoolOr([f[m].Not(), h[m].Not()])
X = {}; byd = {}
bytype = [[d for d in freeD if dT[d] == t] for t in range(4)]
for m in fulls:
    for t, (L, U) in req[m].items():
        terms = []
        for d in bytype[t]:
            if dS[d] <= U:
                v = md.NewBoolVar(""); X[d, m] = v; terms.append(dS[d] * v); byd.setdefault(d, []).append(v)
        md.Add(sum(terms) >= L * f[m]); md.Add(sum(terms) <= U * f[m])
for vs in byd.values():
    if len(vs) > 1: md.AddAtMostOne(vs)
md.Add(sum(En[m] * f[m] for m in fulls) + sum(En[m] * h[m] for m in h) <= CAP - fixed_E)
md.Maximize(sum(val[m] * f[m] for m in fulls) + sum((val[m] // 2) * h[m] for m in h))
for m in fulls: md.AddHint(f[m], 1 if m in full else 0)
for m in h: md.AddHint(h[m], 1 if m in half else 0)
for (d, m), v in X.items(): md.AddHint(v, 1 if owner[d] == m else 0)
print(f"variables x {len(X)}, pleins candidats {len(fulls)}, moitiés {len(h)}", file=sys.stderr, flush=True)
cur = sum(val[m] for m in full) + sum(val[m] // 2 for m in half)
print(f"actuel (hors figés) {cur} + figés {fixed_val} = {cur + fixed_val}", file=sys.stderr, flush=True)


class CB(cp_model.CpSolverSolutionCallback):
    def __init__(self): super().__init__(); self.t0 = time.time()
    def on_solution_callback(self):
        print(f"[{time.time() - self.t0:.0f}s] {self.ObjectiveValue():.0f} (+figés {self.ObjectiveValue() + fixed_val:.0f}) borne {self.BestObjectiveBound():.0f}",
              file=sys.stderr, flush=True)


so = cp_model.CpSolver(); so.parameters.max_time_in_seconds = TLIM; so.parameters.num_workers = WORKERS
so.parameters.random_seed = int(args.get("seed", 1))
st = so.Solve(md, CB())
print(so.StatusName(st), file=sys.stderr)
if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): sys.exit(0)
newowner = [owner[d] if d in locked else None for d in range(len(D))]
for (d, m), v in X.items():
    if so.Value(v): newowner[d] = m
# moitiés : remplissage glouton en non libres (puis libres restants)
ok = True
for m in h:
    if not so.Value(h[m]): continue
    for t, (L, U) in req[m].items():
        avail = sorted((dS[d], d) for d in range(len(D)) if dT[d] == t and newowner[d] is None)
        sizes = [a[0] for a in avail]; got = 0; picks = []; used = set()
        for _ in range(300):
            R, room = L - got, U - got
            if R <= 0: break
            i = bisect.bisect_left(sizes, R)
            while i < len(avail) and (avail[i][1] in used or avail[i][0] > room): i += 1
            if i < len(avail) and avail[i][0] <= room: picks.append(avail[i][1]); got += avail[i][0]; break
            j = bisect.bisect_right(sizes, min(room, R - 1)) - 1
            while j >= 0 and avail[j][1] in used: j -= 1
            if j < 0: break
            picks.append(avail[j][1]); used.add(avail[j][1]); got += avail[j][0]
        if not (L <= got <= U): ok = False; print("échec moitié", m, file=sys.stderr); break
        for d in picks: newowner[d] = m
json.dump({"dataMappings": [[d, m] for d, m in enumerate(newowner) if m is not None],
           "modelMappings": sol["modelMappings"]}, open(OUT, "w"))
