"""Réparation exacte d'une réalisation de plan : ajoute les modèles prévus non placés.

Usage : repair.py <instance.json> <solution.json> <plan.txt> <sortie.json> [time=s] [nb=n] [nr=n] [sub=s] [seed=n]

Pour chaque modèle prévu par le plan mais absent de la solution (meilleure valeur d'abord) :
  - si l'énergie manque, on retire des modèles hors plan de faible rendement ;
  - pour chacun de ses types de données, petit MILP exact (HiGHS) qui ré-affecte les datasets
    d'un voisinage : le nouveau groupe, les groupes de ce type qui dépassent le plus leur borne
    basse, des groupes au hasard, et les datasets non utilisés ; chaque groupe reste dans
    [L, U], les groupes « pleins » ne reçoivent que des datasets libres ;
  - si tous les types sont faisables, le modèle est ajouté (valeur pleine si prévu plein).
Les besoins sourcés ne sont pas traités : seuls les candidats sans source sont essayés.
"""
import sys, json, random, time
import numpy as np
import highspy

TYPES = "ntic"
args = dict(a.split("=", 1) for a in sys.argv[5:])
TLIM = float(args.get("time", 600))
NB = int(args.get("nb", 100))
NR = int(args.get("nr", 50))
SUB = float(args.get("sub", 20))
rng = random.Random(int(args.get("seed", 1)))
DEBUG = args.get("debug", "0") == "1"

inst = json.load(open(sys.argv[1]))
sol = json.load(open(sys.argv[2]))
M, D, CAP = inst["models"], inst["datasets"], inst["energyCap"]
N = len(M)
val = [m["value"] for m in M]
En = [m["energyCost"] for m in M]
req = [{TYPES.index(t): (r["lowerBound"], r["upperBound"]) for t, r in m["dataRequirements"].items()} for m in M]
dT = [TYPES.index(d["dataType"]) for d in D]
dS = [d["size"] for d in D]
dC = [d["isCopyrighted"] for d in D]

plan_full, plan_half = set(), set()
for line in open(sys.argv[3]):
    p = line.split()
    if float(p[1]) > 0.5: plan_full.add(int(p[0]))
    elif float(p[2]) > 0.5: plan_half.add(int(p[0]))

owner = [None] * len(D)
data_of = {}
for d, m in sol["dataMappings"]:
    owner[d] = m
    data_of.setdefault(m, []).append(d)
sources = {s for s, _ in sol["modelMappings"]}
sourced = {}
for s, t in sol["modelMappings"]:
    sourced.setdefault(t, set()).add(dT[data_of[s][0]] if data_of.get(s) else None)
trained = (set(data_of) | set(sourced)) - sources


def is_full(m):
    return m not in sourced and all(not dC[d] for d in data_of.get(m, []))


def value_of(m):
    return val[m] if is_full(m) else val[m] // 2


energy = sum(En[m] for m in trained) + sum(En[s] for s in sources)
total = sum(value_of(m) for m in trained)
print(f"départ : {total}, énergie {energy / CAP:.6f}", file=sys.stderr)


def groups_of_type(t):
    """(modèle, L, U, libres seulement, somme) des groupes de données de type t."""
    out = []
    for m in list(trained) + list(sources):
        ds = [d for d in data_of.get(m, []) if dT[d] == t]
        if not ds:
            continue
        L, U = req[m][t]
        full = m in trained and is_full(m)
        out.append((m, L, U, full, sum(dS[d] for d in ds)))
    return out


def solve_type(t, new_m, new_full):
    """Ré-affectation exacte pour le type t incluant le nouveau groupe. Renvoie {modèle: [datasets]} ou None."""
    L0, U0 = req[new_m][t]
    gs = [g for g in groups_of_type(t) if g[0] != new_m]
    gs.sort(key=lambda g: -(g[4] - g[1]))
    chosen = gs[:NB]
    rest = gs[NB:]
    chosen += rng.sample(rest, min(NR, len(rest)))
    groups = [(new_m, L0, U0, new_full)] + [(g[0], g[1], g[2], g[3]) for g in chosen]
    members = {g[0] for g in chosen} | {new_m}
    pool = [d for d in range(len(D)) if dT[d] == t and (owner[d] is None or owner[d] in members)]
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("time_limit", SUB)
    X = {}
    cost, idx = [], 0
    rows = []
    for gi, (m, L, U, fo) in enumerate(groups):
        cover = {}
        for d in pool:
            if dS[d] > U or (fo and dC[d]):
                continue
            X[d, gi] = idx; cost.append(float(dS[d])); idx += 1
            cover[X[d, gi]] = float(dS[d])
        if not cover:
            return None
        rows.append((float(L), float(U), cover))
    by_d = {}
    for (d, gi), v in X.items():
        by_d.setdefault(d, []).append(v)
    for d, vs in by_d.items():
        if len(vs) > 1:
            rows.append((-np.inf, 1.0, {v: 1.0 for v in vs}))
    nc = idx
    h.addVars(nc, np.zeros(nc), np.ones(nc))
    h.changeColsCost(nc, np.arange(nc, dtype=np.int32), np.array(cost))  # minimise les données utilisées
    h.changeColsIntegrality(nc, np.arange(nc, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * nc))
    for lo, hi, row in rows:
        ii = np.array(list(row.keys()), dtype=np.int32)
        h.addRow(lo, hi, len(ii), ii, np.array(list(row.values())))
    h.run()
    if DEBUG:
        freeVol = sum(dS[d] for d in pool if not dC[d])
        allVol = sum(dS[d] for d in pool)
        needFree = sum(g[1] for g in groups if g[3])
        needAll = sum(g[1] for g in groups)
        print(f"   type {t}: groupes {len(groups)}, pool {len(pool)} (libre {freeVol}, total {allVol}), "
              f"besoin libre {needFree}, besoin total {needAll}, nouveau [{L0},{U0}] -> "
              f"{h.modelStatusToString(h.getModelStatus())}", file=sys.stderr)
    if h.getInfo().primal_solution_status != 2:
        return None
    x = h.getSolution().col_value
    res = {g[0]: [] for g in groups}
    for (d, gi), v in X.items():
        if x[v] > 0.5:
            res[groups[gi][0]].append(d)
    return res


def apply_type(t, res):
    for m, ds in res.items():
        old = [d for d in data_of.get(m, []) if dT[d] == t]
        for d in old:
            owner[d] = None
        keep = [d for d in data_of.get(m, []) if dT[d] != t]
        data_of[m] = keep + ds
        for d in ds:
            owner[d] = m


t0 = time.time()
# modèles prévus pleins mais entraînés à moitié (sans source) : à repasser en plein
upgrades = [m for m in plan_full if m in trained and not is_full(m) and m not in sourced]
cands = sorted(((plan_full | plan_half) - trained - sources) | set(upgrades), key=lambda m: -val[m])
cands = [m for m in cands if all(U >= L for L, U in req[m].values())]
print(f"candidats prévus non placés : {len(cands)}", file=sys.stderr)
added = 0
for m in cands:
    if time.time() - t0 > TLIM:
        break
    full = m in plan_full
    upgrade = m in trained
    gain = (val[m] - val[m] // 2) if upgrade else (val[m] if full else val[m] // 2)
    # énergie : retirer des modèles hors plan au plus faible rendement si nécessaire
    removed = []
    need = (energy + En[m] - CAP) if not upgrade else 0
    if need > 0:
        extra = sorted((x for x in trained if x not in plan_full and x not in plan_half and x not in sourced),
                       key=lambda x: value_of(x) / En[x])
        freed = 0
        for x in extra:
            if freed >= need:
                break
            removed.append(x); freed += En[x]
        if freed < need or sum(value_of(x) for x in removed) >= gain:
            continue
    # sauvegarde pour annulation
    snap_owner, snap_data = owner[:], {k: v[:] for k, v in data_of.items()}
    for x in removed:
        for d in data_of.pop(x, []):
            owner[d] = None
        trained.discard(x)
    ok = True
    for t in req[m]:
        res = solve_type(t, m, full)
        if res is None:
            ok = False
            break
        apply_type(t, res)
    if ok:
        if not upgrade:
            trained.add(m)
            energy += En[m] - sum(En[x] for x in removed)
        # la valeur réelle d'un modèle « moitié » dont tous les datasets sont libres est pleine
        total = sum(value_of(x) for x in trained)
        added += 1
        print(f"[{time.time() - t0:.0f}s] {'passage en plein' if upgrade else 'ajout'} {m} ({'plein' if full else 'moitié'}, +{gain}"
              f"{', retirés ' + str(len(removed)) if removed else ''}) -> {total}", file=sys.stderr, flush=True)
    else:
        if DEBUG:
            print(f"  échec {m} ({'plein' if full else 'moitié'}, gain {gain})", file=sys.stderr)
        owner[:] = snap_owner
        data_of.clear(); data_of.update(snap_data)
        for x in removed:
            trained.add(x)

out = {"dataMappings": [[d, m] for d, m in enumerate(owner) if m is not None],
       "modelMappings": sol["modelMappings"]}
json.dump(out, open(sys.argv[4], "w"))
print(f"fin : {total}, ajoutés {added}", file=sys.stderr)
