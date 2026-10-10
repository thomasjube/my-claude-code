"""Retire les alias (cibles négatives) d'une solution : leurs sources deviennent des modèles entraînés."""
import json, sys
sol = json.load(open(sys.argv[1]))
sol["modelMappings"] = [[s, t] for s, t in sol["modelMappings"] if t >= 0]
json.dump(sol, open(sys.argv[2], "w"))
