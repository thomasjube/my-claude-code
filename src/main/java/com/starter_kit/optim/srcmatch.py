"""Ré-optimisation exacte du côté « sources / cibles entièrement sourcées » (instance 6).

Usage : srcmatch.py <instance.json> <solution.json> <sortie.json> [time=s] [maxk=n]

Les pleins, moitiés à données et cibles partielles (avec leurs sources) sont figés. On retire toutes les
cibles entièrement sourcées et leurs sources ; les datasets ainsi libérés + non utilisés forment le pool.
CP-SAT : sources (modèles à besoin unique, remplis par 1..maxk datasets du pool) et cibles (tous leurs
besoins sourcés), avec, par type, nb sources >= nb besoins des cibles, et l'énergie totale <= cap.
Objectif : valeur des cibles. Amorcé par la solution actuelle.
"""
import sys, json, collections
from ortools.sat.python import cp_model

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
inst = json.load(open(sys.argv[1])); sol = json.load(open(sys.argv[2])); OUT = sys.argv[3]
M, D, CAP = inst["models"], inst["datasets"], inst["energyCap"]
N = len(M)
val = [m["value"] for m in M]; En = [m["energyCost"] for m in M]
req = [{TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()} for m in M]
dT = [TYPES.index(d["dataType"]) for d in D]; dS = [d["size"] for d in D]
owner = [None] * len(D); data_of = collections.defaultdict(list)
for d, m in sol["dataMappings"]:
    owner[d] = m; data_of[m].append(d)
nsrc = collections.Counter(t for _, t in sol["modelMappings"])
fs_targets = {t for t in nsrc if nsrc[t] == len(req[t])}
keep_mm = [(s, t) for s, t in sol["modelMappings"] if t not in fs_targets]
fs_sources = {s for s, t in sol["modelMappings"] if t in fs_targets}
used = (set(data_of) | {t for _, t in sol["modelMappings"]} | {s for s, _ in sol["modelMappings"]})
fixed = used - fs_targets - fs_sources
E_fixed = sum(En[m] for m in fixed)
V_fixed = sum(val[m] if (m not in nsrc and all(not D[d]["isCopyrighted"] for d in data_of[m])) else val[m] // 2
              for m in fixed if m not in {s for s, _ in keep_mm})
pool = [d for d in range(len(D)) if owner[d] is None or owner[d] in fs_sources]
cur = sum(val[m] // 2 for m in fs_targets)
print(f"figé : valeur {V_fixed}, énergie {E_fixed / CAP:.6f} ; cibles entièrement sourcées {len(fs_targets)} ({cur}), "
      f"sources {len(fs_sources)}, pool {len(pool)} datasets", file=sys.stderr, flush=True)
MAXK = int(args.get("maxk", 2))
md = cp_model.CpModel()
cand_src = [m for m in range(N) if len(req[m]) == 1 and m not in fixed and next(iter(req[m].values()))[0] <= next(iter(req[m].values()))[1]]
NS = int(args.get("nsrc", 700))
keep = set(fs_sources)
for t in range(4):
    ct = sorted((m for m in cand_src if next(iter(req[m])) == t), key=lambda m: (req[m][t][0], En[m]))
    keep |= set(ct[:NS])
cand_src = [m for m in cand_src if m in keep]
cand_tgt = [m for m in range(N) if m not in fixed and val[m] // 2 > 0]
R = {m: md.NewBoolVar("") for m in cand_src}   # source
T = {m: md.NewBoolVar("") for m in cand_tgt}   # cible
for m in cand_src:
    if m in T: md.AddBoolOr([R[m].Not(), T[m].Not()])
X = {}; byd = collections.defaultdict(list)
pool_t = [[d for d in pool if dT[d] == t] for t in range(4)]
nv = 0
for m in cand_src:
    t, (L, U) = next(iter(req[m].items()))
    terms = []
    for d in pool_t[t]:
        if dS[d] <= U and (MAXK > 1 or dS[d] >= L):
            v = md.NewBoolVar(""); X[d, m] = v; terms.append(dS[d] * v); byd[d].append(v)
    if not terms:
        md.Add(R[m] == 0); continue
    md.Add(sum(terms) >= L * R[m]); md.Add(sum(terms) <= U * R[m])
    md.Add(sum(X[d, m] for d in pool_t[t] if (d, m) in X) <= MAXK)
for vs in byd.values():
    if len(vs) > 1: md.AddAtMostOne(vs)
for t in range(4):
    md.Add(sum(R[m] for m in cand_src if next(iter(req[m])) == t) >= sum(T[m] for m in cand_tgt if t in req[m]))
md.Add(sum(En[m] * R[m] for m in cand_src) + sum(En[m] * T[m] for m in cand_tgt) <= CAP - E_fixed)
md.Maximize(sum((val[m] // 2) * T[m] for m in cand_tgt))
for m in cand_src: md.AddHint(R[m], 1 if m in fs_sources else 0)
for m in cand_tgt: md.AddHint(T[m], 1 if m in fs_targets else 0)
for (d, m), v in X.items(): md.AddHint(v, 1 if owner[d] == m else 0)
print(f"variables : sources {len(cand_src)}, cibles {len(cand_tgt)}, affectations {len(X)}", file=sys.stderr, flush=True)


class CB(cp_model.CpSolverSolutionCallback):
    def on_solution_callback(self):
        print(f"  {self.WallTime():.0f}s cibles {self.ObjectiveValue():.0f} (total {V_fixed + self.ObjectiveValue():.0f}) "
              f"borne {self.BestObjectiveBound():.0f}", file=sys.stderr, flush=True)


so = cp_model.CpSolver(); so.parameters.max_time_in_seconds = float(args.get("time", 300))
so.parameters.num_workers = int(args.get("workers", 4))
st = so.Solve(md, CB())
print(so.StatusName(st), file=sys.stderr)
if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE) or so.ObjectiveValue() <= cur:
    sys.exit(0)
newowner = [None if (owner[d] is None or owner[d] in fs_sources) else owner[d] for d in range(len(D))]
for (d, m), v in X.items():
    if so.Value(v): newowner[d] = m
srcs = {t: [m for m in cand_src if so.Value(R[m]) and next(iter(req[m])) == t] for t in range(4)}
mm = list(keep_mm)
for m in cand_tgt:
    if so.Value(T[m]):
        for t in req[m]: mm.append((srcs[t].pop(), m))
json.dump({"dataMappings": [[d, m] for d, m in enumerate(newowner) if m is not None],
           "modelMappings": [list(p) for p in mm]}, open(OUT, "w"))
print(f"écrit : {V_fixed + so.ObjectiveValue():.0f}", file=sys.stderr)
