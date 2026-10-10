"""LNS CP-SAT exact avec sources interchangeables (instance 6 : cibles entièrement sourcées).

Usage : cps.py <instance.json> <solution.json> <sortie.json> [time=s] [k=n] [cand=n] [sub=s] [seed=n]
        [workers=n] [unused=n]

Rôles par modèle du voisinage : plein F (datasets libres), moitié H (datasets quelconques),
cible T (tous ses besoins sourcés, aucune donnée), source R (besoin unique, datasets quelconques).
Les sources d'un type sont interchangeables : il suffit que, par type, le nombre de sources
couvre le nombre de besoins des cibles. Les cibles partiellement sourcées et leurs sources sont figées.
"""
import sys, json, random, time
from ortools.sat.python import cp_model

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
TLIM = float(args.get("time", 500)); K = int(args.get("k", 30)); NCAND = int(args.get("cand", 40))
SUB = float(args.get("sub", 10)); WORKERS = int(args.get("workers", 4)); UNUSED = int(args.get("unused", 400))
rng = random.Random(int(args.get("seed", 1))); MODE = int(args.get("mode", 0))
inst = json.load(open(sys.argv[1])); sol = json.load(open(sys.argv[2])); OUT = sys.argv[3]
M, D, CAP = inst["models"], inst["datasets"], inst["energyCap"]
N = len(M)
val = [m["value"] for m in M]; En = [m["energyCost"] for m in M]
req = [{TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()} for m in M]
feasible = [all(U >= L for L, U in r.values()) for r in req]
single = [len(r) == 1 and feasible[i] for i, r in enumerate(req)]
dT = [TYPES.index(d["dataType"]) for d in D]; dS = [d["size"] for d in D]; dC = [d["isCopyrighted"] for d in D]
owner = [None] * len(D); data_of = {}
for d, m in sol["dataMappings"]:
    owner[d] = m; data_of.setdefault(m, []).append(d)
nsrc = {}
for s, t in sol["modelMappings"]:
    nsrc[t] = nsrc.get(t, 0) + 1
# rôles : 'F', 'H', 'T', 'R', 'X' (figé : cible partielle ou sa source)
role = {}
frozen_src = []
for s, t in sol["modelMappings"]:
    if nsrc[t] == len(req[t]):
        role[s] = 'R'; role[t] = 'T'
    else:
        role[s] = 'X'; role[t] = 'X'; frozen_src.append((s, t))
for m, ds in data_of.items():
    if m not in role:
        role[m] = 'F' if all(not dC[d] for d in ds) else 'H'


def value(m):
    r = role.get(m)
    return val[m] if r == 'F' else (val[m] // 2 if r in ('H', 'T', 'X') and not (r == 'X' and m in {s for s, _ in frozen_src}) else 0)


frozen_s = {s for s, _ in frozen_src}


def total_value():
    return sum(val[m] if r == 'F' else val[m] // 2 for m, r in role.items() if r in ('F', 'H', 'T') or (r == 'X' and m not in frozen_s))


def energy_used():
    return sum(En[m] for m in role)


def balance():
    """sources moins besoins sourcés, par type (hors figés)."""
    b = [0] * 4
    for m, r in role.items():
        if r == 'R': b[next(iter(req[m]))] += 1
        elif r == 'T':
            for t in req[m]: b[t] -= 1
    return b


total = total_value()
print(f"départ : {total}, énergie {energy_used() / CAP:.6f}, bilan sources {balance()}", file=sys.stderr, flush=True)
assert min(balance()) >= 0
minL = [sum(L for L, U in r.values()) for r in req]
by_full = sorted((m for m in range(N) if feasible[m] and val[m] > 0), key=lambda m: -val[m] / max(1, minL[m]))
by_tgt = sorted(range(N), key=lambda m: -(val[m] // 2) / max(1, En[m]) / len(req[m]))
by_src = sorted((m for m in range(N) if single[m]), key=lambda m: (req[m][next(iter(req[m]))][0], En[m]))


def iteration():
    global total
    movable = [m for m, r in role.items() if r != 'X']
    t0 = rng.randrange(4)
    free_m = lambda m: m not in role
    if MODE == 1:
        # voisinage « sources » : sources du type t0, cibles l'utilisant, quelques pleins
        srcs = [m for m in movable if role[m] == 'R' and next(iter(req[m])) == t0]
        tg = [m for m in movable if role[m] == 'T' and t0 in req[m]]
        fl = [m for m in movable if role[m] in 'FH' and t0 in req[m]]
        Nn = rng.sample(srcs, min(K * 2 // 3, len(srcs))) + rng.sample(tg, min(K // 3, len(tg))) + rng.sample(fl, min(K // 6, len(fl)))
        types = set()
        for m in Nn: types |= set(req[m])
        c3 = [m for m in by_src[:6000] if free_m(m) and next(iter(req[m])) == t0][:400]
        c2 = [m for m in by_tgt[:4000] if free_m(m) and set(req[m]) == {t0}][:300]
        c1 = [m for m in by_full[:3000] if free_m(m) and set(req[m]) <= types][:300]
        Cn = rng.sample(c3, min(NCAND // 2, len(c3))) + rng.sample(c2, min(NCAND // 3, len(c2))) + rng.sample(c1, min(NCAND // 6, len(c1)))
    else:
        piv = [m for m in movable if t0 in req[m]]
        Nn = rng.sample(piv, min(K, len(piv)))
        types = set()
        for m in Nn: types |= set(req[m])
        c1 = [m for m in by_full[:3000] if free_m(m) and set(req[m]) <= types][:600]
        c2 = [m for m in by_tgt[:3000] if free_m(m) and set(req[m]) <= types][:600]
        c3 = [m for m in by_src[:3000] if free_m(m) and set(req[m]) <= types][:600]
        nc = NCAND // 3
        Cn = rng.sample(c1, min(nc, len(c1))) + rng.sample(c2, min(nc, len(c2))) + rng.sample(c3, min(nc, len(c3)))
    models = list(dict.fromkeys(Nn + Cn))
    nset = set(Nn)
    e_avail = CAP - energy_used() + sum(En[m] for m in Nn)
    pool = [d for d in range(len(D)) if owner[d] is not None and owner[d] in nset]
    unused = [d for d in range(len(D)) if owner[d] is None and dT[d] in types]
    if len(unused) > UNUSED: unused = rng.sample(unused, UNUSED)
    pool += unused
    bal = balance()
    md = cp_model.CpModel(); V = {}; X = {}; byd = {}
    for m in models:
        F = md.NewBoolVar(""); H = md.NewBoolVar(""); T = md.NewBoolVar(""); R = md.NewBoolVar("")
        V[m] = (F, H, T, R)
        md.AddAtMostOne([F, H, T, R])
        if not single[m]: md.Add(R == 0)
        if not feasible[m]: md.Add(F == 0); md.Add(H == 0)
        for t, (L, U) in req[m].items():
            terms = []
            for d in pool:
                if dT[d] == t and dS[d] <= U:
                    v = md.NewBoolVar(""); X[d, m] = v; terms.append(dS[d] * v); byd.setdefault(d, []).append(v)
                    if dC[d]: md.AddImplication(v, F.Not())
            act = F + H + R
            if not terms:
                md.Add(act == 0); continue
            md.Add(sum(terms) >= L * act); md.Add(sum(terms) <= U * act)
    for vs in byd.values():
        if len(vs) > 1: md.AddAtMostOne(vs)
    md.Add(sum(En[m] * sum(V[m]) for m in models) <= e_avail)
    for t in range(4):
        old = sum((1 if role[m] == 'R' and next(iter(req[m])) == t else 0) - (1 if role[m] == 'T' and t in req[m] else 0) for m in Nn)
        new = [V[m][3] for m in models if single[m] and next(iter(req[m])) == t]
        neg = [V[m][2] for m in models if t in req[m]]
        if new or neg:
            md.Add(sum(new) - sum(neg) >= old - bal[t])
    oldv = sum(val[m] if role[m] == 'F' else (val[m] // 2 if role[m] in ('H', 'T') else 0) for m in Nn)
    obj = sum(val[m] * V[m][0] + (val[m] // 2) * (V[m][1] + V[m][2]) for m in models)
    md.Add(obj >= oldv)
    md.Maximize(obj)
    for m in models:
        r = role.get(m) if m in nset else None
        for k, rr in enumerate('FHTR'): md.AddHint(V[m][k], 1 if r == rr else 0)
    for (d, m), v in X.items(): md.AddHint(v, 1 if owner[d] == m else 0)
    so = cp_model.CpSolver(); so.parameters.max_time_in_seconds = SUB; so.parameters.num_workers = WORKERS
    st = so.Solve(md)
    if args.get("debug") == "1":
        print(f"  {so.StatusName(st)} ancien {oldv} obj {so.ObjectiveValue() if st in (2, 4) else -1:.0f} "
              f"borne {so.BestObjectiveBound():.0f} vars {len(X)} modèles {len(models)} pool {len(pool)}", file=sys.stderr, flush=True)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE) or so.ObjectiveValue() <= oldv:
        return 0
    for m in Nn:
        for d in data_of.pop(m, []): owner[d] = None
        del role[m]
    for (d, m), v in X.items():
        if so.Value(v): owner[d] = m; data_of.setdefault(m, []).append(d)
    for m in models:
        for k, rr in enumerate('FHTR'):
            if so.Value(V[m][k]): role[m] = rr
    nt = total_value(); g = nt - total; total = nt
    assert energy_used() <= CAP and min(balance()) >= 0, (energy_used(), balance())
    return g


def write():
    mm = list(frozen_src)
    srcs = {t: [m for m, r in role.items() if r == 'R' and next(iter(req[m])) == t] for t in range(4)}
    for m, r in role.items():
        if r == 'T':
            for t in req[m]: mm.append((srcs[t].pop(), m))
    json.dump({"dataMappings": [[d, m] for d, m in enumerate(owner) if m is not None],
               "modelMappings": [list(p) for p in mm]}, open(OUT, "w"))


t0 = time.time(); it = acc = 0; last = time.time()
write()
while time.time() - t0 < TLIM:
    it += 1
    g = iteration()
    if g > 0:
        acc += 1
        print(f"[{time.time() - t0:.0f}s] it {it} : +{g} -> {total}", file=sys.stderr, flush=True)
        if time.time() - last > 60: write(); last = time.time()
write()
print(f"fin : {total}, itérations {it}, améliorations {acc}, bilan {balance()}", file=sys.stderr)
