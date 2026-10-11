package com.example.rubik.recognition;

import java.util.List;

/**
 * Couleurs de la dernière couche saisies par l'utilisateur (jaune en haut, vert devant).
 *
 * @param top les n×n cases de la face U, ligne par ligne (ligne 0 = côté B, colonne 0 = côté L)
 * @param front ligne du haut de la face F, de gauche à droite vue de face
 * @param right ligne du haut de la face R, de gauche à droite vue de face
 * @param back ligne du haut de la face B, de gauche à droite vue de face
 * @param left ligne du haut de la face L, de gauche à droite vue de face
 */
public record LastLayerInput(List<String> top, List<String> front, List<String> right, List<String> back,
		List<String> left) {
}
