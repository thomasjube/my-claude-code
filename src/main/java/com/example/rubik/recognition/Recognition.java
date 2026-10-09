package com.example.rubik.recognition;

/**
 * Résultat de l'identification d'un cas.
 *
 * @param found {@code true} si l'état saisi a été reconnu
 * @param message explication à afficher
 * @param caseId identifiant du cas reconnu ({@code null} si déjà résolu ou non reconnu)
 * @param caseName nom du cas reconnu
 * @param preAuf mouvement de U à faire avant l'algorithme
 * @param algorithm algorithme du cas
 * @param postAuf mouvement de U à faire après l'algorithme
 * @param solution séquence complète à exécuter
 */
public record Recognition(boolean found, String message, String caseId, String caseName, String preAuf,
		String algorithm, String postAuf, String solution) {

	static Recognition notFound(String message) {
		return new Recognition(false, message, null, null, null, null, null, null);
	}

}
