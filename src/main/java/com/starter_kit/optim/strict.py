"""Correcteur strict : test_solution.py + refus des identifiants hors bornes (correctif de la plateforme)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from test_solution import getSolutionScore


def strict_score(solution_txt, dataset_txt):
    inst = json.loads(dataset_txt)
    try:
        sol = json.loads(solution_txt)
        n = len(inst["models"])
        for key in ("dataMappings", "modelMappings"):
            for a, b in sol.get(key, []):
                if key == "modelMappings" and not (0 <= a < n and 0 <= b < n):
                    return 0, False, f"Model {a if not 0 <= a < n else b} does not exist"
    except Exception as e:
        return 0, False, str(e)
    return getSolutionScore(solution_txt, dataset_txt, show_details=False)
