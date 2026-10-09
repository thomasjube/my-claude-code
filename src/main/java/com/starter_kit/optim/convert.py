"""Convertit une instance JSON en format texte pour le solveur C++.

Format : N_modeles N_datasets energyCap
         puis par modèle : valeur energie k (type L U)*k   (type = indice dans 'ntic')
         puis par dataset : type taille copyright
"""
import json, sys

TYPES = "ntic"

def main(src, dst):
    inst = json.load(open(src))
    models, datasets = inst["models"], inst["datasets"]
    assert all(m["id"] == i for i, m in enumerate(models))
    assert all(d["id"] == i for i, d in enumerate(datasets))
    with open(dst, "w") as out:
        out.write(f"{len(models)} {len(datasets)} {inst['energyCap']}\n")
        for m in models:
            reqs = m["dataRequirements"]
            parts = [str(m["value"]), str(m["energyCost"]), str(len(reqs))]
            for t, b in reqs.items():
                parts += [str(TYPES.index(t)), str(b["lowerBound"]), str(b["upperBound"])]
            out.write(" ".join(parts) + "\n")
        for d in datasets:
            out.write(f"{TYPES.index(d['dataType'])} {d['size']} {d['isCopyrighted']}\n")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
