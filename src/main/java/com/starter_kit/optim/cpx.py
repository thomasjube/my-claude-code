"""LNS CP-SAT exact pour les instances à pénurie de données (6) : rôles et datasets ré-optimisés ensemble.

Usage : cpx.py <instance.json> <solution.json> <sortie.json> [time=s] [k=n] [cand=n] [sub=s] [seed=n] [workers=n]

Voisinage : k modèles entraînés sans source (pleins ou moitiés) + candidats non entraînés.
Pool : tous leurs datasets + datasets non utilisés. Pour chaque modèle : plein (F, datasets libres
seulement), moitié (H, n'importe quels datasets) ou exclu ; chaque besoin dans [L, U] si actif.
Énergie respectée. Les sources et leurs cibles ne bougent pas.
"""
import sys, json, random, time
from ortools.sat.python import cp_model

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
TLIM = float(args.get("time", 500)); K = int(args.get("k", 30)); NCAND = int(args.get("cand", 40))
SUB = float(args.get("sub", 10)); WORKERS = int(args.get("workers", 4)); UNUSED = int(args.get("unused", 400)); rng = random.Random(int(args.get("seed", 1)))
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


def is_full(m):
    return m not in sourced and all(not dC[d] for d in data_of.get(m, []))


def value_of(m):
    return val[m] if is_full(m) else val[m] // 2


def energy_used():
    return sum(En[m] for m in trained) + sum(En[s] for s in sources)


total = sum(value_of(m) for m in trained)
print(f"départ : {total}, énergie {energy_used() / CAP:.6f}, libres {sum(o is None for o in owner)}", file=sys.stderr, flush=True)
minL = [sum(L for L, U in r.values()) for r in req]
ratio_order = sorted((m for m in range(N) if feasible[m] and val[m] > 0), key=lambda m: -val[m] / max(1, minL[m]))


def iteration():
    global total
    movable = [m for m in trained if m not in sourced]
    # voisinage localisé : un type pivot, modèles le partageant, plus quelques autres
    t0 = rng.randrange(4)
    pivot = [m for m in movable if t0 in req[m]]
    Nn = rng.sample(pivot, min(K, len(pivot)))
    types = set()
    for m in Nn: types |= set(req[m])
    pool_new = [m for m in ratio_order[:3000] if m not in trained and m not in sources and set(req[m]) <= types]
    Cn = rng.sample(pool_new[:600], min(NCAND, len(pool_new[:600])))
    models = list(dict.fromkeys(Nn + Cn))
    e_avail = CAP - energy_used() + sum(En[m] for m in Nn)
    nset = set(Nn)
    pool = [d for d in range(len(D)) if owner[d] is not None and owner[d] in nset]
    unused = [d for d in range(len(D)) if owner[d] is None and dT[d] in types]
    if len(unused) > UNUSED:
        unused = rng.sample(unused, UNUSED)
    pool += unused
    md = cp_model.CpModel(); F, H, X = {}, {}, {}; byd = {}
    for m in models:
        F[m] = md.NewBoolVar(""); H[m] = md.NewBoolVar(""); md.AddBoolOr([F[m].Not(), H[m].Not()])
        for t, (L, U) in req[m].items():
            terms = []
            for d in pool:
                if dT[d] == t and dS[d] <= U:
                    v = md.NewBoolVar(""); X[d, m] = v; terms.append(dS[d] * v); byd.setdefault(d, []).append(v)
                    if dC[d]: md.AddImplication(v, F[m].Not())
            if not terms:
                md.Add(F[m] + H[m] == 0); continue
            md.Add(sum(terms) >= L * (F[m] + H[m])); md.Add(sum(terms) <= U * (F[m] + H[m]))
    for vs in byd.values():
        if len(vs) > 1: md.AddAtMostOne(vs)
    md.Add(sum(En[m] * (F[m] + H[m]) for m in models) <= e_avail)
    old = sum(value_of(m) for m in Nn)
    obj = sum(val[m] * F[m] + (val[m] // 2) * H[m] for m in models)
    md.Add(obj >= old)
    md.Maximize(obj)
    for m in models:
        md.AddHint(F[m], 1 if (m in nset and is_full(m)) else 0)
        md.AddHint(H[m], 1 if (m in nset and not is_full(m)) else 0)
    for (d, m), v in X.items():
        md.AddHint(v, 1 if owner[d] == m else 0)
    so = cp_model.CpSolver(); so.parameters.max_time_in_seconds = SUB; so.parameters.num_workers = WORKERS
    st = so.Solve(md)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE) or so.ObjectiveValue() <= old:
        return 0
    for m in Nn:
        for d in data_of.pop(m, []): owner[d] = None
        trained.discard(m)
    for (d, m), v in X.items():
        if so.Value(v):
            owner[d] = m; data_of.setdefault(m, []).append(d)
    for m in models:
        if so.Value(F[m]) or so.Value(H[m]): trained.add(m)
    new_total = sum(value_of(m) for m in trained)
    g = new_total - total; total = new_total
    assert energy_used() <= CAP
    return g


def write():
    json.dump({"dataMappings": [[d, m] for d, m in enumerate(owner) if m is not None],
               "modelMappings": sol["modelMappings"]}, open(OUT, "w"))


t0 = time.time(); it = acc = 0; last = time.time()
while time.time() - t0 < TLIM:
    it += 1
    g = iteration()
    if g > 0:
        acc += 1
        print(f"[{time.time() - t0:.0f}s] it {it} : +{g} -> {total}", file=sys.stderr, flush=True)
        if time.time() - last > 60: write(); last = time.time()
write()
print(f"fin : {total}, itérations {it}, améliorations {acc}", file=sys.stderr)
