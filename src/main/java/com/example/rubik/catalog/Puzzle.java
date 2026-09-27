package com.example.rubik.catalog;

import java.util.List;
import java.util.Optional;

/**
 * Un cube et sa méthode de résolution.
 *
 * @param id identifiant ({@code 2x2}, {@code 3x3}, {@code 4x4})
 * @param name nom affiché
 * @param size nombre de tranches par arête
 * @param summary présentation de la méthode
 * @param stages étapes, dans l'ordre de résolution
 */
public record Puzzle(String id, String name, int size, String summary, List<Stage> stages) {

	public Puzzle {
		stages = List.copyOf(stages);
	}

	public Optional<Stage> stage(String stageId) {
		return this.stages.stream().filter((stage) -> stage.id().equals(stageId)).findFirst();
	}

}
