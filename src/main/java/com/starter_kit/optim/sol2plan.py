"""Convertit une solution (json) en plan (format lp.py : id x y s a z_1..z_k) pour tester la réalisation.

Usage : sol2plan.py <instance.json> <solution.json> <plan.txt>
"""
import sys, json, collections

inst = json.load(open(sys.argv[1])); sol = json.load(open(sys.argv[2]))
M, D = inst["models"], inst["datasets"]
dof = collections.defaultdict(list)
for d, m in sol["dataMappings"]: dof[m].append(d)
srcs = {s for s, _ in sol["modelMappings"]}
tsrc = collections.defaultdict(set)
for s, t in sol["modelMappings"]: tsrc[t].add(next(iter(M[s]["dataRequirements"])))
with open(sys.argv[3], "w") as f:
    for i, m in enumerate(M):
        rq = list(m["dataRequirements"])
        x = y = s = 0; z = [0] * len(rq)
        if i in srcs: s = 1
        elif i in dof or i in tsrc:
            if i not in tsrc and all(not D[d]["isCopyrighted"] for d in dof[i]): x = 1
            else:
                y = 1; z = [1 if t in tsrc[i] else 0 for t in rq]
        f.write(f"{i} {x} {y} {s} 0 " + " ".join(map(str, z)) + "\n")
