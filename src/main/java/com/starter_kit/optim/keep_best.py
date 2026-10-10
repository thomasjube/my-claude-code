"""Copie une solution dans ../solutions/<instance>_submission.json si elle est valide et meilleure.

Usage : python3 keep_best.py <instance> <solution.json>   (instance ex. 2_medium)
"""
import sys, os, shutil, fcntl
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from test_solution import getSolutionScore

def score(inst, path):
    if not os.path.exists(path):
        return 0
    s, ok, _ = getSolutionScore(open(path).read(), open(os.path.join(HERE, "..", "datasets", inst + ".json")).read(), False)
    return s if ok else 0

inst, cand = sys.argv[1], sys.argv[2]
dest = os.path.join(HERE, "..", "solutions", inst + "_submission.json")
new = score(inst, cand)
# verrou : plusieurs exécutions parallèles peuvent comparer et copier en même temps
with open(dest + ".lock", "w") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    old = score(inst, dest)
    if new > old:
        shutil.copy(cand, dest + ".tmp")
        os.replace(dest + ".tmp", dest)
        print(f"{inst}: {old} -> {new} (nouveau meilleur)")
    else:
        print(f"{inst}: {new} (meilleur conservé : {old})")
