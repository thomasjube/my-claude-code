package com.example.rubik.catalog;

import java.util.List;

/** Vues exposées par l'API. */
public final class CatalogViews {

	private CatalogViews() {
	}

	public record PuzzleSummary(String id, String name, int size, String summary, List<StageSummary> stages) {
	}

	public record StageSummary(String id, String title, int caseCount) {
	}

	public record PuzzleView(String id, String name, int size, String summary, List<StageView> stages) {
	}

	public record StageView(String id, String title, String summary, List<String> tips, DiagramType diagramType,
			boolean recognizable, List<CaseView> cases) {
	}

	/**
	 * @param moveCount nombre de mouvements (rotations du cube exclues)
	 * @param setup séquence qui, depuis un cube résolu, produit le cas (inverse de l'algorithme)
	 */
	public record CaseView(String id, String name, String group, String algorithm, int moveCount, String setup,
			Diagram diagram) {
	}

}
