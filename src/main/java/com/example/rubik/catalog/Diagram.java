package com.example.rubik.catalog;

import java.util.List;
import java.util.Map;

/**
 * Représentation d'un cas : couleurs des six faces (lignes puis colonnes, convention des
 * patrons) et, pour les PLL, flèches de permutation sur la face U.
 *
 * @param type type de diagramme
 * @param size taille du cube
 * @param faces couleurs par face ({@code U R F D L B}), {@code gray} pour les cases masquées
 * @param arrows flèches de permutation (face U)
 */
public record Diagram(DiagramType type, int size, Map<String, List<String>> faces, List<Arrow> arrows) {

	/**
	 * Déplacement d'une pièce de la face U, de sa position actuelle vers sa destination.
	 *
	 * @param from case de départ {@code [ligne, colonne]}
	 * @param to case d'arrivée {@code [ligne, colonne]}
	 * @param bothWays {@code true} si les deux pièces s'échangent
	 */
	public record Arrow(int[] from, int[] to, boolean bothWays) {
	}

}
