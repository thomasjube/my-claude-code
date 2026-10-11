"""Sac à dos exact des moitiés : pleins, sources et cibles fixés, choix optimal des modèles « moitié »
(données non libres, vérifiées par remplissage glouton) sous l'énergie restante.

Usage : knap.py <instance.json> <solution.json> <sortie.json> [time=s] [demote=1]
demote=1 : un plein peut aussi redevenir moitié (libère ses datasets libres, non réutilisés ici).
"""
import sys, json, bisect
from ortools.sat.python import cp_model

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
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
trained = (set(data_of) | sourced) - sources
full = {m for m in trained if m not in sourced and all(not dC[d] for d in data_of[m])}
half = trained - full - sourced
fixedE = sum(En[m] for m in full | sourced | sources)
fixedV = sum(val[m] for m in full) + sum(val[m] // 2 for m in sourced)
cands = [m for m in range(N) if feasible[m] and m not in full and m not in sourced and m not in sources and val[m] // 2 > 0]
import random
rng = random.Random(1)
banned = set()
cur = sum(val[m] // 2 for m in half)


def dp_fill(t, L, U, avail):
    """sous-ensemble de datasets disponibles (taille, id) de somme dans [L, U] (DP par bitset)."""
    c = [a for a in avail if a[0] <= U]
    rng.shuffle(c); c = c[:400]
    reach = [1]
    for sz, _ in c: reach.append(reach[-1] | (reach[-1] << sz))
    mask = reach[-1] >> L
    if mask == 0: return None
    tgt = L + (mask & -mask).bit_length() - 1
    if tgt > U: return None
    picks = []
    for k in range(len(c), 0, -1):
        if not (reach[k - 1] >> tgt) & 1:
            picks.append(c[k - 1][1]); tgt -= c[k - 1][0]
    return picks


def fill(t, L, U):
    avail = sorted((dS[d], d) for d in range(len(D)) if dT[d] == t and owner[d] is None)
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
    if L <= got <= U: return picks
    return dp_fill(t, L, U, avail)


snap = owner[:]
for rnd in range(20):
    md = cp_model.CpModel()
    h = {m: md.NewBoolVar("") for m in cands if m not in banned}
    md.Add(sum(En[m] * h[m] for m in h) <= CAP - fixedE)
    md.Maximize(sum((val[m] // 2) * h[m] for m in h))
    for m in h: md.AddHint(h[m], 1 if m in half else 0)
    so = cp_model.CpSolver(); so.parameters.max_time_in_seconds = float(args.get("time", 60)); so.parameters.num_workers = 4
    st = so.Solve(md)
    print(f"moitiés actuelles {cur}, sac à dos {so.ObjectiveValue():.0f} borne {so.BestObjectiveBound():.0f} ({so.StatusName(st)})", file=sys.stderr, flush=True)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE) or so.ObjectiveValue() <= cur: sys.exit(0)
    newh = sorted((m for m in h if so.Value(h[m])), key=lambda m: -sum(L for L, U in req[m].values()))
    owner[:] = snap
    keep = set(newh) & half
    for m in half - keep:
        for d in data_of.get(m, []): owner[d] = None
    bad = None
    for m in newh:
        if m in keep: continue
        for t, (L, U) in req[m].items():
            picks = fill(t, L, U)
            if picks is None: bad = m; break
            for d in picks: owner[d] = m
        if bad is not None: break
    if bad is None: break
    print("échec remplissage", bad, "-> exclu", file=sys.stderr); banned.add(bad)
else:
    sys.exit(0)
json.dump({"dataMappings": [[d, m] for d, m in enumerate(owner) if m is not None],
           "modelMappings": sol["modelMappings"]}, open(OUT, "w"))
print(f"écrit : {fixedV + so.ObjectiveValue():.0f}", file=sys.stderr)
