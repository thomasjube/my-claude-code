"""Échanges exacts plein <-> moitié sur les datasets libres (HiGHS).

Usage : swap.py <instance.json> <solution.json> <sortie.json> [time=s] [nb=n] [sub=s] [cands=n] [seed=n]

Pour un candidat (modèle entraîné à moitié sans source, ou modèle non entraîné qui tient dans
l'énergie restante), on construit un MILP sur les datasets libres :
  - y[m] = 1 si le modèle m reste/devient « plein » (tous ses besoins en données libres) ;
  - voisinage : les nb groupes pleins de chaque type concerné qui dépassent le plus leur borne
    basse + des groupes au hasard ; datasets = libres de ces groupes + libres non utilisés ;
  - objectif : maximiser la valeur gagnée (v/2 pour chaque plein, valeur pleine pour un nouveau).
Un modèle rétrogradé (y = 0) reprend des datasets non libres (glouton exact) ; si c'est
impossible, l'échange est annulé. Les modèles avec sources ne sont pas touchés.
"""
import sys, json, random, time, bisect
import numpy as np


TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[4:])
TLIM = float(args.get("time", 500))
NB = int(args.get("nb", 60))
NR = int(args.get("nr", 20))
SUB = float(args.get("sub", 30))
NC = int(args.get("cands", 200))
rng = random.Random(int(args.get("seed", 1)))
inst = json.load(open(sys.argv[1])); sol = json.load(open(sys.argv[2])); OUT = sys.argv[3]
M, D, CAP = inst["models"], inst["datasets"], inst["energyCap"]
N = len(M)
val = [m["value"] for m in M]; En = [m["energyCost"] for m in M]
req = [{TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()} for m in M]
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


energy = sum(En[m] for m in trained) + sum(En[s] for s in sources)
total = sum(value_of(m) for m in trained)
print(f"départ : {total}", file=sys.stderr)


def fill_cop(t, L, U, exclude):
    """Remplit [L, U] avec des datasets non libres non utilisés de type t (glouton + paire)."""
    avail = sorted((dS[d], d) for d in range(len(D)) if dT[d] == t and dC[d] and owner[d] is None and d not in exclude)
    sizes = [a[0] for a in avail]
    got, picks, used = 0, [], set()
    while got < L:
        R, room = L - got, U - got
        i = bisect.bisect_left(sizes, R)
        while i < len(avail) and avail[i][1] in used: i += 1
        if i < len(avail) and avail[i][0] <= room:
            picks.append(avail[i][1]); return picks
        j = bisect.bisect_right(sizes, min(room, R - 1)) - 1
        while j >= 0 and avail[j][1] in used: j -= 1
        if j < 0: return None
        picks.append(avail[j][1]); used.add(avail[j][1]); got += avail[j][0]
    return picks


def try_candidate(c):
    global total, energy
    new = c not in trained
    if new and energy + En[c] > CAP:
        return False
    types = list(req[c])
    nb_models = set()
    groups = []  # (modèle, type, L, U)
    for t in types:
        gs = []
        for m in trained:
            if m == c or m in sourced or not is_full(m) or t not in req[m]:
                continue
            ds = [d for d in data_of.get(m, []) if dT[d] == t]
            gs.append((sum(dS[d] for d in ds) - req[m][t][0], m))
        gs.sort(reverse=True)
        chosen = [m for _, m in gs[:NB]]
        rest = [m for _, m in gs[NB:]]
        chosen += rng.sample(rest, min(NR, len(rest)))
        for m in chosen:
            nb_models.add(m)
            groups.append((m, t) + req[m][t])
        groups.append((c, t) + req[c][t])
    # les modèles du voisinage gardent leurs autres types fixes : seuls les types listés sont ré-affectés
    in_type = {t: {g[0] for g in groups if g[1] == t} for t in types}
    pool = {t: [d for d in range(len(D)) if dT[d] == t and not dC[d] and
                (owner[d] is None or owner[d] in in_type[t])] for t in types}
    models = sorted(nb_models | {c})
    from ortools.sat.python import cp_model
    md = cp_model.CpModel()
    Y = {m: md.NewBoolVar(f"y{m}") for m in models}
    X = {}
    by_d = {}
    for gi, (m, t, L, U) in enumerate(groups):
        terms = []
        for d in pool[t]:
            if dS[d] <= U:
                v = md.NewBoolVar(""); X[d, gi] = v; terms.append(dS[d] * v)
                by_d.setdefault(d, []).append(v)
        md.Add(sum(terms) >= L * Y[m]) if terms else md.Add(Y[m] == 0)
        if terms:
            md.Add(sum(terms) <= U * Y[m])
    for vs in by_d.values():
        if len(vs) > 1: md.AddAtMostOne(vs)
    md.Maximize(sum((val[m] if (m == c and new) else val[m] - val[m] // 2) * Y[m] for m in models))
    for m in nb_models: md.AddHint(Y[m], 1)
    md.AddHint(Y[c], 0)
    for gi, (m, t, L, U) in enumerate(groups):
        if m == c: continue
        cur = {d for d in data_of.get(m, []) if dT[d] == t}
        for d in pool[t]:
            if (d, gi) in X: md.AddHint(X[d, gi], 1 if d in cur else 0)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SUB
    solver.parameters.num_workers = int(args.get("workers", 4))
    st = solver.Solve(md)
    if args.get("debug") == "1":
        print(f"  cand {c} ({'nouveau' if new else 'moitié'}, v={val[c]}) : {solver.StatusName(st)} obj {solver.ObjectiveValue():.0f} "
              f"borne {solver.BestObjectiveBound():.0f} actuel {sum(val[m] - val[m] // 2 for m in nb_models):.0f} "
              f"vars {len(X)}", file=sys.stderr, flush=True)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return False
    x = {k: solver.Value(v) for k, v in X.items()}
    yv = {m: solver.Value(v) for m, v in Y.items()}
    if not yv[c]:
        return False
    old_val = sum(value_of(m) for m in models if m in trained)
    # nouvelle affectation
    snap_owner, snap_data, snap_trained = owner[:], {k: v[:] for k, v in data_of.items()}, set(trained)
    for gi, (m, t, L, U) in enumerate(groups):
        for d in [d for d in data_of.get(m, []) if dT[d] == t]:
            owner[d] = None
        data_of[m] = [d for d in data_of.get(m, []) if dT[d] != t]
    for (d, gi), v in x.items():
        if v:
            m = groups[gi][0]; owner[d] = m; data_of[m].append(d)
    # rétrogradés : besoins sans données -> non libres ; candidat : autres besoins déjà libres
    ok = True
    for gi, (m, t, L, U) in enumerate(groups):
        if yv[m]: continue
        picks = fill_cop(t, L, U, set())
        if picks is None: ok = False; break
        for d in picks: owner[d] = m; data_of[m].append(d)
    if ok:
        trained.add(c)
        new_val = sum(value_of(m) for m in models)
        if new_val <= old_val:
            ok = False
    if not ok:
        owner[:] = snap_owner; data_of.clear(); data_of.update(snap_data); trained.clear(); trained.update(snap_trained)
        return False
    if new: energy += En[c]
    total = sum(value_of(m) for m in trained)
    return True


t0 = time.time()
halves = [m for m in trained if not is_full(m) and m not in sourced]
untrained = [m for m in range(N) if m not in trained and m not in sources and all(U >= L for L, U in req[m].values())
             and En[m] <= CAP - energy]
cands = sorted(halves, key=lambda m: -val[m])[:NC] + sorted(untrained, key=lambda m: -val[m])[:NC // 4]
if args.get("only"):
    cands = [int(x) for x in args["only"].split(",")]
print(f"candidats : {len(cands)} (moitiés {len(halves)}, non entraînés tenant dans l'énergie {len(untrained)})",
      file=sys.stderr)
acc = 0
for c in cands:
    if time.time() - t0 > TLIM: break
    if try_candidate(c):
        acc += 1
        print(f"[{time.time() - t0:.0f}s] {c} -> {total}", file=sys.stderr, flush=True)
json.dump({"dataMappings": [[d, m] for d, m in enumerate(owner) if m is not None],
           "modelMappings": sol["modelMappings"]}, open(OUT, "w"))
print(f"fin : {total}, échanges {acc}", file=sys.stderr)
