"""Réalisation incrémentale d'un plan à partir d'une solution existante (instances 2, 4, 7).

Usage : applyplan.py <instance.json> <solution.json> <plan.txt> <sortie.json> [nb=n] [sub=s] [seed=n]

1. retire les pleins et moitiés (sans source) absents du plan ;
2. par type, MILP exact (HiGHS) : les groupes des nouveaux pleins + nb groupes pleins existants (les plus en
   excès + aléatoires) se partagent leurs datasets libres et les libres non utilisés ; les groupes existants
   restent satisfaits, on maximise la valeur des nouveaux groupes satisfaits ;
3. un nouveau plein n'est gardé que si tous ses types sont satisfaits (deux passes) ;
4. moitiés prévues absentes : remplissage glouton en datasets non libres si l'énergie le permet.
Les sources et cibles sourcées ne sont pas modifiées.
"""
import sys, json, random, bisect, collections
import numpy as np
import highspy

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[5:])
NB = int(args.get("nb", 250)); SUB = float(args.get("sub", 60)); rng = random.Random(int(args.get("seed", 1)))
inst = json.load(open(sys.argv[1])); sol = json.load(open(sys.argv[2])); OUT = sys.argv[4]
M, D, CAP = inst["models"], inst["datasets"], inst["energyCap"]
val = [m["value"] for m in M]; En = [m["energyCost"] for m in M]
req = [{TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()} for m in M]
dT = [TYPES.index(d["dataType"]) for d in D]; dS = [d["size"] for d in D]; dC = [d["isCopyrighted"] for d in D]
PX, PY = set(), set()
for line in open(sys.argv[3]):
    p = line.split()
    if float(p[1]) > .5: PX.add(int(p[0]))
    if float(p[2]) > .5: PY.add(int(p[0]))
owner = [None] * len(D); dof = collections.defaultdict(list)
for d, m in sol["dataMappings"]: owner[d] = m; dof[m].append(d)
srcs = {s for s, _ in sol["modelMappings"]}; tg = {t for _, t in sol["modelMappings"]}
full = {m for m in dof if m not in tg and m not in srcs and all(not dC[d] for d in dof[m])}
half = (set(dof) | tg) - srcs - full


def value():
    return sum(val[m] for m in full) + sum(val[m] // 2 for m in half)


def energy():
    return sum(En[m] for m in full | half | srcs)


v0 = value()
# 1. retraits
for m in list(full - PX) + [m for m in half - PY if m not in tg]:
    for d in dof.pop(m, []): owner[d] = None
    full.discard(m); half.discard(m)
new = sorted(PX - full - srcs - tg, key=lambda m: -val[m])
# énergie : si nécessaire, une moitié hors plan... (le plan respecte l'énergie ; on vérifie à la fin)
print(f"départ {v0}, après retraits {value()}, nouveaux pleins {len(new)}", file=sys.stderr, flush=True)


def solve_type(t, newm):
    gs = [m for m in full if t in req[m]]
    gs.sort(key=lambda m: -(sum(dS[d] for d in dof[m] if dT[d] == t) - req[m][t][0]))
    chosen = gs[:NB] + rng.sample(gs[NB:], min(NB // 3, len(gs[NB:])))
    members = set(chosen)
    pool = [d for d in range(len(D)) if dT[d] == t and not dC[d] and (owner[d] is None or owner[d] in members)]
    groups = [(m, True) for m in chosen] + [(m, False) for m in newm if t in req[m]]
    h = highspy.Highs(); h.setOptionValue("output_flag", False); h.setOptionValue("time_limit", SUB)
    X = {}; cost = []; rows = []
    Yv = {}
    for gi, (m, old) in enumerate(groups):
        L, U = req[m][t]
        cov = {}
        for d in pool:
            if dS[d] <= U:
                X[d, gi] = len(cost); cost.append(0.0); cov[X[d, gi]] = float(dS[d])
        if old:
            rows.append((float(L), float(U), cov))
        else:
            Yv[gi] = len(cost); cost.append(-float(val[m]))
            lo = dict(cov); lo[Yv[gi]] = -float(L); hi = dict(cov); hi[Yv[gi]] = -float(U)
            rows.append((0.0, highspy.kHighsInf, lo)); rows.append((-highspy.kHighsInf, 0.0, hi))
    byd = collections.defaultdict(list)
    for (d, gi), v in X.items(): byd[d].append(v)
    for vs in byd.values():
        if len(vs) > 1: rows.append((-highspy.kHighsInf, 1.0, {v: 1.0 for v in vs}))
    n = len(cost)
    h.addVars(n, np.zeros(n), np.ones(n))
    h.changeColsCost(n, np.arange(n, dtype=np.int32), np.array(cost))
    h.changeColsIntegrality(n, np.arange(n, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * n))
    for lo, hi, row in rows:
        h.addRow(lo, hi, len(row), np.array(list(row.keys()), dtype=np.int32), np.array(list(row.values())))
    # indication : affectation actuelle
    x0 = np.zeros(n)
    for (d, gi), v in X.items():
        if owner[d] == groups[gi][0]: x0[v] = 1
    s0 = highspy.HighsSolution(); s0.col_value = list(x0); s0.value_valid = True; h.setSolution(s0)
    h.run()
    if h.getInfo().primal_solution_status != 2:
        return None
    x = h.getSolution().col_value
    res = {m: [] for m, _ in groups}
    for (d, gi), v in X.items():
        if x[v] > .5: res[groups[gi][0]].append(d)
    sat = {groups[gi][0] for gi, v in Yv.items() if x[v] > .5}
    return res, sat


for rnd in range(2):
    if not new: break
    results = {}
    for t in range(4):
        r = solve_type(t, new)
        if r is None:
            print(f"type {t} : pas de solution", file=sys.stderr); results[t] = ({}, set())
        else:
            results[t] = r
    ok = [m for m in new if all(m in results[t][1] for t in req[m])]
    print(f"passe {rnd} : nouveaux pleins satisfaits partout {len(ok)}/{len(new)}", file=sys.stderr, flush=True)
    if len(ok) == len(new) or rnd == 1:
        okset = set(ok)
        for t in range(4):
            res, _ = results[t]
            for m, ds in res.items():
                if m in full or m in okset:
                    for d in [d for d in dof[m] if dT[d] == t]: owner[d] = None
                    dof[m] = [d for d in dof[m] if dT[d] != t]
            for m, ds in res.items():
                if m in full or m in okset:
                    for d in ds: owner[d] = m; dof[m].append(d)
        full |= okset
        new = [m for m in new if m not in okset]
        break
    new = ok  # deuxième passe avec les seuls modèles réalisables partout

# moitiés prévues absentes
def fill(t, L, U):
    avail = sorted((dS[d], d) for d in range(len(D)) if dT[d] == t and owner[d] is None and dC[d])
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
    return picks if L <= got <= U else None


for m in sorted(PY - half - full - srcs - tg, key=lambda m: -val[m]):
    if energy() + En[m] > CAP: continue
    allp = []
    for t, (L, U) in req[m].items():
        p = fill(t, L, U)
        if p is None: allp = None; break
        for d in p: owner[d] = m
        allp += p
    if allp is None:
        for d in range(len(D)):
            if owner[d] == m: owner[d] = None
        continue
    dof[m] = allp; half.add(m)
assert energy() <= CAP, "énergie dépassée"
json.dump({"dataMappings": [[d, m] for d, m in enumerate(owner) if m is not None],
           "modelMappings": sol["modelMappings"]}, open(OUT, "w"))
print(f"fin : {value()} (énergie {energy() / CAP:.6f})", file=sys.stderr)
