"""Statistiques d'une solution : gaspillage de données, sources, valeur pleine/moitié."""
import sys, json, collections
inst = json.load(open(sys.argv[1])); sol = json.load(open(sys.argv[2]))
M, D = inst["models"], inst["datasets"]; N = len(M)
fill = collections.defaultdict(lambda: collections.Counter()); cop = collections.defaultdict(int)
for d, m in sol["dataMappings"]:
    fill[m][D[d]["dataType"]] += D[d]["size"]; cop[m] |= D[d]["isCopyrighted"]
sources = {s for s, _ in sol["modelMappings"]}
sourced = collections.defaultdict(set)
for s, t in sol["modelMappings"]:
    sourced[t].add(next(iter(M[s]["dataRequirements"])))
targets = (set(fill) | set(sourced)) - sources
waste = used = 0; full = half = alias = 0; vfull = vhalf = 0
for t in targets:
    m = M[t]
    if t < 0: alias += 1
    for ty, r in m["dataRequirements"].items():
        if ty in sourced[t]: continue
        used += fill[t][ty]; waste += fill[t][ty] - r["lowerBound"]
    if cop[t] or sourced[t]: half += 1; vhalf += m["value"] // 2
    else: full += 1; vfull += m["value"]
srcdata = sum(sum(fill[s].values()) for s in sources)
tot = sum(d["size"] for d in D); usedall = sum(D[d]["size"] for d, _ in sol["dataMappings"])
print(f"cibles {len(targets)} (pleines {full}: {vfull}, moitié {half}: {vhalf}, alias {alias}), sources {len(sources)}")
print(f"données utilisées {usedall}/{tot} ({100*usedall/tot:.1f}%), dont sources {srcdata}; gaspillage cibles {waste} ({100*waste/max(1,used):.2f}%)")
freeLeft = sum(d["size"] for i, d in enumerate(D) if not d["isCopyrighted"]) - sum(D[d]["size"] for d, _ in sol["dataMappings"] if not D[d]["isCopyrighted"])
print(f"données libres restantes {freeLeft}")
