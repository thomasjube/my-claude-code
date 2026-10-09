"""Valide une solution avec test_solution.py et affiche le score (sortie : score ou 0)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from test_solution import getSolutionScore
score, ok, msg = getSolutionScore(open(sys.argv[2]).read(), open(sys.argv[1]).read(), show_details=False)
print(score if ok else f"INVALIDE: {msg}")
