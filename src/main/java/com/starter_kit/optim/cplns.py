"""LNS à voisinages larges avec CP-SAT : choix des modèles ET affectation exacte des datasets libres.

Usage : cplns.py <instance.json> <solution.json> <sortie.json> [time=s] [k=n] [cand=n] [sub=s] [seed=n]
        [workers=n] [copfrac=f]

Pour les instances où les datasets non libres sont abondants (2, 4, 7). À chaque itération :
  - voisinage N : k modèles « pleins » tirés au hasard (avec leurs datasets libres) ;
  - candidats C : modèles « moitié » sans source et modèles non entraînés à bon rendement ;
  - CP-SAT : pour chaque modèle de N ∪ C, plein (f), moitié (h) ou exclu ; les pleins reçoivent
    exactement des datasets libres (libérés + non utilisés) dans chaque fenêtre [L, U] ; énergie
    totale respectée ; volume non libre des nouvelles moitiés <= volume non libre disponible ;
  - application si la valeur augmente : les nouvelles moitiés sont remplies en non libre (glouton
    exact), sinon annulation.
Les modèles alimentés par des sources et les sources ne sont pas touchés.
"""
import sys, json, random, time, bisect
from ortools.sat.python import cp_model

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
TLIM = float(args.get("time", 500)); K = int(args.get("k", 40)); NCAND = int(args.get("cand", 60))
SUB = float(args.get("sub", 30)); WORKERS = int(args.get("workers", 4)); COPFRAC = float(args.get("copfrac", 0.9))
rng = random.Random(int(args.get("seed", 1)))
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
print(f"départ : {total}, énergie {energy_used() / CAP:.6f}", file=sys.stderr, flush=True)


def fill_cop(t, L, U, taken):
    """Datasets non libres non utilisés de type t, somme dans [L, U] (glouton : gros puis finisseur)."""
    avail = sorted((dS[d], d) for d in range(len(D)) if dT[d] == t and dC[d] and owner[d] is None and d not in taken)
    sizes = [a[0] for a in avail]
    got, picks, used = 0, [], set()
    for _ in range(200):
        R, room = L - got, U - got
        if R <= 0:
            return picks
        i = bisect.bisect_left(sizes, R)
        while i < len(avail) and (avail[i][1] in used or avail[i][0] > room): i += 1
        if i < len(avail) and avail[i][0] <= room:
            picks.append(avail[i][1]); return picks
        j = bisect.bisect_right(sizes, min(room, R - 1)) - 1
        while j >= 0 and avail[j][1] in used: j -= 1
        if j < 0:
            return None
        picks.append(avail[j][1]); used.add(avail[j][1]); got += avail[j][0]
    return None


ratio_order = sorted((m for m in range(N) if feasible[m] and val[m] > 0), key=lambda m: -val[m] / En[m])


def iteration():
    global total
    fulls = [m for m in trained if m not in sourced and is_full(m)]
    halves = [m for m in trained if m not in sourced and not is_full(m)]
    Nn = rng.sample(fulls, min(K, len(fulls)))
    Ch = rng.sample(halves, min(NCAND // 2, len(halves)))
    # non entraînés à bon rendement (tirage biaisé parmi les meilleurs ratios)
    pool_new = [m for m in ratio_order[:4000] if m not in trained and m not in sources]
    Cn = rng.sample(pool_new[:400], min(NCAND // 2, len(pool_new[:400])))
    models = list(dict.fromkeys(Nn + Ch + Cn))
    cur_in = [m for m in models if m in trained]
    e_avail = CAP - energy_used() + sum(En[m] for m in cur_in)
    # datasets libres : ceux des modèles du voisinage + non utilisés
    freepool = {t: [] for t in range(4)}
    for d in range(len(D)):
        if not dC[d] and (owner[d] is None or owner[d] in set(Nn)):
            freepool[dT[d]].append(d)
    copvol = [0] * 4
    for d in range(len(D)):
        if dC[d] and (owner[d] is None or owner[d] in set(Ch)):
            copvol[dT[d]] += dS[d]
    md = cp_model.CpModel()
    F, H, X = {}, {}, {}
    by_d = {}
    for m in models:
        F[m] = md.NewBoolVar(""); H[m] = md.NewBoolVar(""); md.AddBoolOr([F[m].Not(), H[m].Not()])
        for t, (L, U) in req[m].items():
            terms = []
            for d in freepool[t]:
                if dS[d] <= U:
                    v = md.NewBoolVar(""); X[d, m] = v; terms.append(dS[d] * v)
                    by_d.setdefault(d, []).append(v)
            if terms:
                md.Add(sum(terms) >= L * F[m]); md.Add(sum(terms) <= U * F[m])
            else:
                md.Add(F[m] == 0)
    for vs in by_d.values():
        if len(vs) > 1: md.AddAtMostOne(vs)
    md.Add(sum(En[m] * (F[m] + H[m]) for m in models) <= e_avail)
    for t in range(4):
        terms = [req[m][t][0] * H[m] for m in models if t in req[m]]
        if terms:
            md.Add(sum(terms) <= int(copvol[t] * COPFRAC))
    md.Maximize(sum(val[m] * F[m] + (val[m] // 2) * H[m] for m in models))
    # indication : état actuel
    for m in models:
        md.AddHint(F[m], 1 if (m in trained and is_full(m)) else 0)
        md.AddHint(H[m], 1 if (m in trained and not is_full(m)) else 0)
    for (d, m), v in X.items():
        md.AddHint(v, 1 if owner[d] == m else 0)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SUB
    solver.parameters.num_workers = WORKERS
    st = solver.Solve(md)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return 0
    old = sum(value_of(m) for m in cur_in)
    new = solver.ObjectiveValue()
    if args.get("debug") == "1":
        print(f"  {solver.StatusName(st)} ancien {old} nouveau {new:.0f} borne {solver.BestObjectiveBound():.0f} "
              f"vars {len(X)} énergie dispo {e_avail - sum(En[m] for m in cur_in)}", file=sys.stderr, flush=True)
    if new <= old:
        return 0
    # application
    snap_owner, snap_data, snap_trained = owner[:], {k: v[:] for k, v in data_of.items()}, set(trained)
    fv = {m: solver.Value(F[m]) for m in models}; hv = {m: solver.Value(H[m]) for m in models}
    keep_half = {m for m in Ch if hv[m]}           # moitiés inchangées : gardent leurs données
    for m in models:
        if m in keep_half:
            continue
        for d in data_of.pop(m, []):
            owner[d] = None
        trained.discard(m)
    for (d, m), v in X.items():
        if solver.Value(v):
            owner[d] = m; data_of.setdefault(m, []).append(d)
    for m in models:
        if fv[m]:
            trained.add(m)
    ok = True
    for m in models:
        if hv[m] and m not in keep_half:
            for t, (L, U) in req[m].items():
                picks = fill_cop(t, L, U, set())
                if picks is None:
                    ok = False; break
                for d in picks:
                    owner[d] = m; data_of.setdefault(m, []).append(d)
            if not ok:
                break
            trained.add(m)
    new_total = sum(value_of(m) for m in trained)
    if not ok or new_total <= total or energy_used() > CAP:
        owner[:] = snap_owner; data_of.clear(); data_of.update(snap_data); trained.clear(); trained.update(snap_trained)
        return 0
    gain = new_total - total
    total = new_total
    return gain


def write():
    json.dump({"dataMappings": [[d, m] for d, m in enumerate(owner) if m is not None],
               "modelMappings": sol["modelMappings"]}, open(OUT, "w"))


t0 = time.time(); it = acc = 0; last = 0
while time.time() - t0 < TLIM:
    it += 1
    g = iteration()
    if g > 0:
        acc += 1
        print(f"[{time.time() - t0:.0f}s] it {it} : +{g} -> {total}", file=sys.stderr, flush=True)
        if time.time() - last > 60:
            write(); last = time.time()
write()
print(f"fin : {total}, itérations {it}, améliorations {acc}", file=sys.stderr)
