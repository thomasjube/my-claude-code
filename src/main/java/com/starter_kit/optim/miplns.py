"""LNS à sous-MILP : réaffectation exacte des datasets sur un voisinage.

Usage : miplns.py <instance.json> <solution.json> <sortie.json> [time=s] [k=n] [cand=n] [pool=n] [seed=n]

À chaque itération :
  - on retire k modèles entraînés « sans source » partageant un type de données ;
  - on ajoute des modèles candidats non utilisés ;
  - on résout avec HiGHS le sous-problème exact : choix plein / moitié / rien, affectation des
    datasets (libérés + échantillon de datasets non utilisés) dans les fenêtres [L, U],
    budget d'énergie libéré ;
  - on garde la nouvelle affectation si la valeur ne baisse pas.
Les modèles alimentés par des sources (et les sources) ne sont pas touchés.
"""
import sys, json, random, time
import numpy as np
import highspy

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
T_LIMIT = float(args.get("time", 600))
K = int(args.get("k", 20))
CAND = int(args.get("cand", 30))
POOL = int(args.get("pool", 150))
SUB_T = float(args.get("subtime", 10))
rng = random.Random(int(args.get("seed", 1)))
DEBUG = args.get("debug", "0") == "1"
PLAN = args.get("plan")

inst = json.load(open(sys.argv[1]))
sol = json.load(open(sys.argv[2]))
OUT = sys.argv[3]
M, D, CAP = inst["models"], inst["datasets"], inst["energyCap"]
N = len(M)
val = [m["value"] for m in M]
En = [m["energyCost"] for m in M]
reqs = [{TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()} for m in M]
dsT = [TYPES.index(d["dataType"]) for d in D]
dsS = [d["size"] for d in D]
dsC = [d["isCopyrighted"] for d in D]

# ---------------------------------------------------------------- état
owner = [None] * len(D)            # id brut du modèle propriétaire
sources = {s for s, _ in sol["modelMappings"]}
srcOf = {}
for s, t in sol["modelMappings"]:
    srcOf.setdefault(t, []).append(s)
dataOf = {}
for d, m in sol["dataMappings"]:
    owner[d] = m
    dataOf.setdefault(m, []).append(d)
targets = (set(dataOf) | set(srcOf)) - sources
fixed = set()                      # cibles avec sources (non modifiables), alias, sources
movable = {}                       # modèle -> liste de datasets
for t in targets:
    if t < 0 or t in srcOf:
        fixed.add(t)
    else:
        movable[t] = list(dataOf.get(t, []))


def item_value(m, ds):
    return val[m] // 2 if any(dsC[d] for d in ds) else val[m]


def energy_total():
    e = sum(En[s] for s in sources)
    for t in targets:
        e += En[t + N if t < 0 else t]
    return e


used_models = {t + N if t < 0 else t for t in targets} | sources
real_used = set(movable) | {t for t in fixed if t >= 0} | sources
energy = energy_total()
value = sum(item_value(m, ds) for m, ds in movable.items()) + sum(
    (val[t + N] // 2 if t < 0 else val[t] // 2) for t in fixed)
print(f"départ : valeur {value}, énergie {energy / CAP:.5f}, modifiables {len(movable)}", file=sys.stderr)

unused_by_type = [[d for d in range(len(D)) if owner[d] is None and dsT[d] == t] for t in range(4)]
unused_set = [set(u) for u in unused_by_type]
feasible = [all(U >= L for (L, U) in reqs[m].values()) for m in range(N)]
ratio = [val[m] / En[m] for m in range(N)]
planned = set()
if PLAN:
    for line in open(PLAN):
        p = line.split()
        if float(p[1]) > 0.5 or float(p[2]) > 0.5:
            planned.add(int(p[0]))


def write(path):
    dm = []
    for d, m in enumerate(owner):
        if m is not None:
            dm.append([d, m])
    out = {"dataMappings": dm, "modelMappings": [[s, t] for s, t in sol["modelMappings"]]}
    json.dump(out, open(path, "w"))


def solve_sub(R, C, t_focus):
    """Sous-MILP sur les modèles R (retirés) + C (candidats). Renvoie (valeur, affectation) ou None."""
    models = list(R) + list(C)
    freed = [d for m in R for d in movable[m]]
    pool = [set() for _ in range(4)]
    for d in freed:
        pool[dsT[d]].add(d)
    types_needed = set()
    for m in models:
        types_needed |= set(reqs[m])
    for t in types_needed:
        u = unused_by_type[t]
        free_u = [d for d in u if not dsC[d]]
        cop_u = [d for d in u if dsC[d]]
        pool[t].update(free_u if len(free_u) <= POOL else rng.sample(free_u, POOL))
        pool[t].update(cop_u if len(cop_u) <= POOL else rng.sample(cop_u, POOL))
    e_free = CAP - energy + sum(En[m] for m in R)

    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("time_limit", SUB_T)
    h.setOptionValue("mip_rel_gap", 0.0)
    cost, lb, ub = [], [], []

    def var(c):
        cost.append(-c); lb.append(0.0); ub.append(1.0)
        return len(cost) - 1

    rows = []
    F, H, X = {}, {}, {}
    for m in models:
        F[m] = var(val[m]); H[m] = var(val[m] // 2)
        rows.append((-np.inf, 1.0, {F[m]: 1.0, H[m]: 1.0}))
        for t, (L, U) in reqs[m].items():
            cover, cnt = {}, {}
            for d in pool[t]:
                if dsS[d] > U:
                    continue
                X[d, m] = v = var(0.0)
                cover[v] = float(dsS[d])
                if dsC[d]:
                    rows.append((-np.inf, 0.0, {v: 1.0, H[m]: -1.0}))
            r_lo = dict(cover); r_lo[F[m]] = r_lo.get(F[m], 0) - L; r_lo[H[m]] = r_lo.get(H[m], 0) - L
            rows.append((0.0, np.inf, r_lo))
            r_hi = dict(cover); r_hi[F[m]] = r_hi.get(F[m], 0) - U; r_hi[H[m]] = r_hi.get(H[m], 0) - U
            rows.append((-np.inf, 0.0, r_hi))
    by_ds = {}
    for (d, m), v in X.items():
        by_ds.setdefault(d, []).append(v)
    for d, vs in by_ds.items():
        if len(vs) > 1:
            rows.append((-np.inf, 1.0, {v: 1.0 for v in vs}))
    rows.append((-np.inf, float(e_free), {**{F[m]: float(En[m]) for m in models}, **{H[m]: float(En[m]) for m in models}}))

    nc = len(cost)
    h.addVars(nc, np.array(lb), np.array(ub))
    h.changeColsCost(nc, np.arange(nc, dtype=np.int32), np.array(cost))
    h.changeColsIntegrality(nc, np.arange(nc, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * nc))
    for lo, hi, row in rows:
        idx = np.array(list(row.keys()), dtype=np.int32)
        h.addRow(lo, hi, len(idx), idx, np.array(list(row.values()), dtype=float))
    # solution de départ : l'état actuel (modèles retirés tels quels)
    start = np.zeros(nc)
    for m in R:
        cop = any(dsC[d] for d in movable[m])
        start[H[m] if cop else F[m]] = 1
        for d in movable[m]:
            if (d, m) in X:
                start[X[d, m]] = 1
    try:
        hs = highspy.HighsSolution()
        hs.col_value = list(start)
        hs.value_valid = True
        h.setSolution(hs)
    except Exception:
        pass
    h.run()
    st = h.getModelStatus()
    if DEBUG:
        info = h.getInfo()
        print(f"  sous-MILP : {nc} var, {len(rows)} lignes, statut {h.modelStatusToString(st)}, "
              f"obj {-info.objective_function_value:.0f}, borne {-info.mip_dual_bound:.0f}", file=sys.stderr)
    if h.getInfo().primal_solution_status != 2:
        return None
    x = h.getSolution().col_value
    newval = -h.getInfo().objective_function_value
    assign = {}
    for m in models:
        if x[F[m]] > 0.5 or x[H[m]] > 0.5:
            assign[m] = [d for t in reqs[m] for d in pool[t] if (d, m) in X and x[X[d, m]] > 0.5]
    return newval, assign, e_free


def apply(R, assign):
    global energy, value
    for m in R:
        for d in movable[m]:
            owner[d] = None
            unused_by_type[dsT[d]].append(d)
        del movable[m]
        energy -= En[m]
        real_used.discard(m)
    for m, ds in assign.items():
        movable[m] = ds
        real_used.add(m)
        energy += En[m]
        for d in ds:
            owner[d] = m
    for t in range(4):
        unused_by_type[t] = [d for d in unused_by_type[t] if owner[d] is None]
    value = sum(item_value(m, ds) for m, ds in movable.items()) + sum(
        (val[t + N] // 2 if t < 0 else val[t] // 2) for t in fixed)


t0 = time.time()
it = acc = 0
last_save = 0
while time.time() - t0 < T_LIMIT:
    it += 1
    t = rng.randrange(4)
    with_t = [m for m in movable if t in reqs[m]]
    if not with_t:
        continue
    halves = [m for m in with_t if any(dsC[d] for d in movable[m])]
    nh = min(len(halves), K // 2) if rng.random() < 0.7 else 0
    R = rng.sample(halves, nh) if nh else []
    rest = [m for m in with_t if m not in set(R)]
    R += rng.sample(rest, min(K - len(R), len(rest)))
    old = sum(item_value(m, movable[m]) for m in R)
    e_free = CAP - energy + sum(En[m] for m in R)
    cands = [m for m in range(N) if m not in real_used and feasible[m] and t in reqs[m] and En[m] <= e_free and val[m] > 0]
    cands.sort(key=lambda m: -(ratio[m] * (100 if m in planned else 1)) * rng.uniform(0.7, 1.3))
    C = cands[:CAND]
    res = solve_sub(R, C, t)
    if res is None:
        continue
    newval, assign, _ = res
    # valeur réelle (une « moitié » sans dataset non libre vaut la valeur pleine)
    real_new = sum(item_value(m, ds) for m, ds in assign.items())
    if DEBUG:
        print(f"  ancien {old}, nouveau {real_new}", file=sys.stderr)
    if real_new > old:
        apply(R, assign)
        acc += 1
        print(f"[{time.time() - t0:.0f}s] it {it} : +{real_new - old} -> {value}", file=sys.stderr, flush=True)
        if time.time() - last_save > 30:
            write(OUT); last_save = time.time()
write(OUT)
print(f"fin : valeur {value}, itérations {it}, améliorations {acc}", file=sys.stderr)
