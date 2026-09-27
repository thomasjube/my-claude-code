package com.example.rubik.recognition;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import com.example.rubik.catalog.AlgCase;
import com.example.rubik.catalog.CaseStates;
import com.example.rubik.catalog.Catalog;
import com.example.rubik.catalog.DiagramType;
import com.example.rubik.catalog.Puzzle;
import com.example.rubik.catalog.Stage;
import com.example.rubik.cube.Cube;
import com.example.rubik.cube.Face;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatIllegalArgumentException;

class RecognitionServiceTest {

	private final RecognitionService service = new RecognitionService();

	private final Random random = new Random(42);

	@Test
	void recognizesEveryCaseWhateverTheAuf() {
		for (Puzzle puzzle : Catalog.puzzles()) {
			for (Stage stage : puzzle.stages()) {
				if (!stage.recognizable()) {
					continue;
				}
				for (AlgCase algCase : stage.cases()) {
					int n = puzzle.size();
					String setup = CaseStates.auf(this.random.nextInt(4)) + " " + algCase.algorithm() + " "
							+ CaseStates.auf(this.random.nextInt(4));
					Cube state = CaseStates.caseState(n, setup);
					Recognition result = this.service.recognize(puzzle, stage, input(state));
					String label = puzzle.id() + " " + algCase.name();
					assertThat(result.found()).as(label).isTrue();
					Cube after = state.copy().apply(result.solution());
					if (stage.diagramType() == DiagramType.OLL) {
						assertThat(CaseStates.topOriented(after)).as(label).isTrue();
						assertThat(CaseStates.lowerLayersSolved(after, false)).as(label).isTrue();
					}
					else {
						assertThat(after.isSolved()).as(label).isTrue();
					}
				}
			}
		}
	}

	@Test
	void recognizesPllWhenHoldingAnotherSideInFront() {
		Puzzle puzzle = threeByThree();
		Stage pll = puzzle.stage("pll").orElseThrow();
		AlgCase tPerm = pll.cases().stream().filter((c) -> c.name().equals("T")).findFirst().orElseThrow();
		// cube tenu avec le rouge devant : même état, couleurs latérales décalées
		Cube state = CaseStates.caseState(3, "y " + tPerm.algorithm() + " y'");
		Recognition result = this.service.recognize(puzzle, pll, input(state));
		assertThat(result.found()).isTrue();
		assertThat(result.caseName()).isEqualTo("T");
	}

	@Test
	void reportsSolvedAndInvalidStates() {
		Puzzle puzzle = threeByThree();
		Stage pll = puzzle.stage("pll").orElseThrow();
		Recognition solved = this.service.recognize(puzzle, pll, input(Cube.solved(3).apply("U")));
		assertThat(solved.found()).isTrue();
		assertThat(solved.caseId()).isNull();
		assertThat(solved.solution()).isEqualTo("U'");

		Recognition notOriented = this.service.recognize(puzzle, pll,
				input(CaseStates.caseState(3, "R U R' U R U2 R'")));
		assertThat(notOriented.found()).isFalse();

		LastLayerInput impossible = input(Cube.solved(3).apply("R U R' U'"));
		assertThat(this.service.recognize(puzzle, puzzle.stage("oll").orElseThrow(), impossible).found())
			.isFalse();

		assertThatIllegalArgumentException().isThrownBy(() -> this.service.recognize(puzzle, pll,
				new LastLayerInput(List.of("yellow"), List.of(), List.of(), List.of(), List.of())));
	}

	private static Puzzle threeByThree() {
		return Catalog.puzzles().stream().filter((p) -> p.id().equals("3x3")).findFirst().orElseThrow();
	}

	static LastLayerInput input(Cube cube) {
		int n = cube.size();
		Face[] colors = cube.colors();
		List<String> top = new ArrayList<>();
		for (int i = 0; i < n * n; i++) {
			top.add(colors[Face.U.ordinal() * n * n + i].color());
		}
		return new LastLayerInput(top, row(colors, Face.F, n), row(colors, Face.R, n), row(colors, Face.B, n),
				row(colors, Face.L, n));
	}

	private static List<String> row(Face[] colors, Face face, int n) {
		List<String> row = new ArrayList<>();
		for (int col = 0; col < n; col++) {
			row.add(colors[face.ordinal() * n * n + col].color());
		}
		return row;
	}

}
