#!/usr/bin/env python3
"""Solveur 'IA responsables'.

Usage :
  python3 solver.py [secondes]            lit une instance sur stdin, écrit la solution sur stdout
  python3 solver.py --all [secondes]      résout tous les datasets/*.json, valide avec test_solution.py

Principe :
  - un décodeur glouton construit une solution en parcourant les modèles dans un ordre donné ;
  - pour chaque besoin, on prend les datasets libres puis non libres (malus de valeur) ;
  - si les données manquent, on tente un modèle générateur à besoin unique (coût énergie seulement) ;
  - une recherche itérée explore des ordres bruités et garde la meilleure solution.
"""
import sys, json, bisect, random, math, time, glob, os

INF = float("inf")


def build_pools(datasets):
    """Pools triés (taille, id) par type : datasets libres et non libres séparés."""
    free = {t: [] for t in "ntic"}
    cop = {t: [] for t in "ntic"}
    for d in datasets:
        (cop if d["isCopyrighted"] else free)[d["dataType"]].append((d["size"], d["id"]))
    for pools in (free, cop):
        for t in pools:
            pools[t].sort()
    return free, cop


def build_singles(models):
    """Modèles à besoin unique, par type, triés par coût énergétique (candidats générateurs)."""
    singles = {t: [] for t in "ntic"}
    for i, m in enumerate(models):
        if len(m["dataRequirements"]) == 1:
            (t,) = m["dataRequirements"].keys()
            singles[t].append(i)
    for t in singles:
        singles[t].sort(key=lambda i: models[i]["energyCost"])
    return singles


def fill(pools, lo, hi):
    """Prend des datasets (plus grand qui tient dans la place restante) jusqu'à atteindre lo.

    pools : suite de (liste triée, est_non_libre). Ne dépasse jamais hi.
    Retourne (total, malus, [(pool, item) retirés]). L'appelant doit restaurer en cas d'échec.
    """
    got = 0
    penal = False
    picks = []
    for pool, is_cop in pools:
        while got < lo:
            idx = bisect.bisect_right(pool, (hi - got, INF)) - 1
            if idx < 0:
                break
            item = pool.pop(idx)
            picks.append((pool, item))
            got += item[0]
            if is_cop:
                penal = True
        if got >= lo:
            break
    return got, penal, picks


def restore(picks):
    for pool, item in picks:
        bisect.insort(pool, item)


def decode(order, models, cap, base_free, base_cop, singles, scan=40):
    """Solution gloutonne en suivant l'ordre donné.

    Retourne (valeur totale, [(id dataset, id modèle)], [(id source, id cible)], énergie utilisée).
    """
    free = {t: list(v) for t, v in base_free.items()}
    cop = {t: list(v) for t, v in base_cop.items()}
    used = [False] * len(models)
    used_energy = 0
    total = 0
    dm, mm = [], []

    for mi in order:
        if used[mi]:
            continue
        m = models[mi]
        cost = m["energyCost"]
        if used_energy + cost > cap:
            continue

        all_picks = []   # pour annuler si le modèle est refusé
        assign = []      # (dataset, modèle propriétaire) pour ce modèle et ses sources
        srcs = []
        src_energy = 0
        penal = False
        ok = True

        for t, b in m["dataRequirements"].items():
            lo, hi = b["lowerBound"], b["upperBound"]
            got, p, picks = fill(((free[t], False), (cop[t], True)), lo, hi)
            if got >= lo:
                all_picks += picks
                assign += [(it[1], m["id"]) for _, it in picks]
                penal = penal or p
                continue

            # Données insuffisantes : on tente un modèle générateur de ce type.
            restore(picks)
            penal = True
            src = None
            for s in singles[t][:scan]:
                if used[s] or s == mi:
                    continue
                sm = models[s]
                if used_energy + cost + src_energy + sm["energyCost"] > cap:
                    continue
                sb = sm["dataRequirements"][t]
                # Le générateur consomme d'abord les non libres : aucun malus pour lui.
                g2, _, p2 = fill(((cop[t], True), (free[t], False)), sb["lowerBound"], sb["upperBound"])
                if g2 >= sb["lowerBound"]:
                    src = s
                    all_picks += p2
                    assign += [(it[1], sm["id"]) for _, it in p2]
                    break
                restore(p2)
            if src is None:
                ok = False
                break
            used[src] = True
            srcs.append(src)
            src_energy += models[src]["energyCost"]

        value = m["value"] // 2 if penal else m["value"]
        if not ok or value <= 0:
            restore(all_picks)
            for s in srcs:
                used[s] = False
            continue

        used[mi] = True
        used_energy += cost + src_energy
        total += value
        dm += assign
        mm += [(models[s]["id"], m["id"]) for s in srcs]

    return total, dm, mm, used_energy


def make_order(models, cap, data_total, alpha=1.0, noise=0.0, rng=None):
    """Ordre des modèles par « valeur / ressource consommée ».

    La ressource mélange énergie (part alpha) et quantité minimale de données (1 - alpha),
    chacune normalisée par son total. alpha = 1 : pur tri valeur / énergie.
    """
    keys = []
    for i, m in enumerate(models):
        if m["value"] <= 0:
            continue
        need = sum(b["lowerBound"] for b in m["dataRequirements"].values())
        res = alpha * m["energyCost"] / cap + (1 - alpha) * need / max(1, data_total)
        dens = m["value"] / max(res, 1e-18)
        if noise:
            dens *= math.exp(rng.gauss(0.0, noise))
        keys.append((-dens, i))
    keys.sort()
    return [i for _, i in keys]


def solve(inst, budget=10.0, seed=1, log=sys.stderr):
    models, cap = inst["models"], inst["energyCap"]
    base_free, base_cop = build_pools(inst["datasets"])
    singles = build_singles(models)
    data_total = sum(d["size"] for d in inst["datasets"])
    t0 = time.time()

    def run(order):
        return decode(order, models, cap, base_free, base_cop, singles)

    best = run(make_order(models, cap, data_total, 1.0))
    print(f"  glouton (valeur/énergie) : valeur={best[0]} énergie={best[3]}/{cap} "
          f"({time.time()-t0:.1f}s)", file=log)
    alt = run(make_order(models, cap, data_total, 0.0))
    print(f"  glouton (valeur/données) : valeur={alt[0]}", file=log)
    if alt[0] > best[0]:
        best = alt

    rng = random.Random(seed)
    it = 0
    while time.time() - t0 < budget:
        it += 1
        alpha = rng.random()
        noise = rng.uniform(0.0, 0.3)
        cand = run(make_order(models, cap, data_total, alpha, noise, rng))
        if cand[0] > best[0]:
            best = cand
            print(f"  itér {it}: valeur={best[0]} (alpha {alpha:.2f}, bruit {noise:.2f})", file=log)
    print(f"  final : valeur={best[0]} après {it} itérations", file=log)
    return best


def to_solution(result):
    _, dm, mm, _ = result
    return {
        "dataMappings": [[ds, mid] for ds, mid in dm],
        "modelMappings": [[s, t] for s, t in mm],
    }


def check_ids(inst):
    assert all(m["id"] == i for i, m in enumerate(inst["models"])), "id modèle != index"
    assert all(d["id"] == i for i, d in enumerate(inst["datasets"])), "id dataset != index"


def main():
    args = sys.argv[1:]
    if args and args[0] == "--all":
        budget = float(args[1]) if len(args) > 1 else 10.0
        from test_solution import getSolutionScore
        os.makedirs("solutions", exist_ok=True)
        for path in sorted(glob.glob("datasets/*.json")):
            txt = open(path).read()
            inst = json.loads(txt)
            check_ids(inst)
            print(f"\n{os.path.basename(path)}", file=sys.stderr)
            result = solve(inst, budget)
            sol_txt = json.dumps(to_solution(result), indent=2)
            score, valid, msg = getSolutionScore(sol_txt, txt, show_details=False)
            if valid:
                name = os.path.basename(path).replace(".", "_submission.")
                with open(os.path.join("solutions", name), "w") as f:
                    f.write(sol_txt)
                print(f"  VALIDE, score = {score}", file=sys.stderr)
            else:
                print(f"  INVALIDE : {msg}", file=sys.stderr)
    else:
        budget = float(args[0]) if args else 10.0
        inst = json.loads(sys.stdin.read())
        check_ids(inst)
        print(json.dumps(to_solution(solve(inst, budget))))


if __name__ == "__main__":
    main()
