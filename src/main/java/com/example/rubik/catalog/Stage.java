package com.example.rubik.catalog;

import java.util.List;

/**
 * Étape de résolution (F2L, OLL, PLL...).
 *
 * @param id identifiant de l'étape
 * @param title titre affiché
 * @param summary explication de l'étape
 * @param tips conseils pratiques
 * @param diagramType représentation des cas
 * @param recognizable {@code true} si l'identification d'un cas à partir de la dernière
 * couche est proposée
 * @param cases cas de l'étape
 */
public record Stage(String id, String title, String summary, List<String> tips, DiagramType diagramType,
		boolean recognizable, List<AlgCase> cases) {

	public Stage {
		tips = List.copyOf(tips);
		cases = List.copyOf(cases);
	}

}
