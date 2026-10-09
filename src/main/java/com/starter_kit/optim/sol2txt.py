"""Convertit une solution JSON en format texte (lignes « D dataset modèle » / « M source cible »)."""
import json, sys
sol = json.load(open(sys.argv[1]))
with open(sys.argv[2], "w") as f:
    for d, m in sol["dataMappings"]:
        f.write(f"D {d} {m}\n")
    for s, t in sol["modelMappings"]:
        f.write(f"M {s} {t}\n")
