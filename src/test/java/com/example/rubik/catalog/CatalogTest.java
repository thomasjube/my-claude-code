package com.example.rubik.catalog;

import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.stream.Collectors;

import com.example.rubik.cube.Cube;
import com.example.rubik.cube.Face;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Vérifie chaque algorithme du catalogue sur le moteur : il doit résoudre un cas de son étape
 * sans rien casser d'autre, et les cas d'une étape doivent être tous différents.
 */
class CatalogTest {

	private static final Map<String, Puzzle> PUZZLES = Catalog.puzzles()
		.stream()
		.collect(Collectors.toMap(Puzzle::id, Function.identity()));

	private static Stage stage(String puzzle, String stage) {
		return PUZZLES.get(puzzle).stage(stage).orElseThrow();
	}

	@Test
	void everyCaseIsValidForItsStage() {
		for (Puzzle puzzle : PUZZLES.values()) {
			int n = puzzle.size();
			for (Stage stage : puzzle.stages()) {
				for (AlgCase algCase : stage.cases()) {
					Cube state = CaseStates.caseState(n, algCase.algorithm());
					String label = puzzle.id() + " " + algCase.name();
					assertThat(state.isSolved()).as(label + " ne doit pas être résolu").isFalse();
					switch (stage.diagramType()) {
						case F2L -> assertThat(CaseStates.lowerLayersSolved(state, true)).as(label).isTrue();
						case OLL -> {
							assertThat(CaseStates.lowerLayersSolved(state, false)).as(label).isTrue();
							assertThat(CaseStates.topOriented(state)).as(label).isFalse();
						}
						case PLL -> assertThat(CaseStates.lowerLayersSolved(state, false)).as(label).isTrue();
						case NONE -> throw new AssertionError("Cas sans diagramme : " + label);
					}
				}
			}
		}
	}

	@Test
	void stagesCoverEveryCaseExactlyOnce() {
		assertDistinct("3x3", "f2l", 41);
		assertDistinct("3x3", "oll", 57);
		assertDistinct("3x3", "pll", 21);
		assertDistinct("2x2", "premiere-couche", 5);
		assertDistinct("2x2", "oll", 7);
		assertDistinct("2x2", "pll", 2);
	}

	private static void assertDistinct(String puzzleId, String stageId, int expected) {
		Stage stage = stage(puzzleId, stageId);
		int n = PUZZLES.get(puzzleId).size();
		Set<String> signatures = new HashSet<>();
		signatures.add(CaseStates.canonicalSignature(n, "", stage.diagramType()));
		for (AlgCase algCase : stage.cases()) {
			assertThat(signatures.add(CaseStates.canonicalSignature(n, algCase.algorithm(), stage.diagramType())))
				.as(puzzleId + " " + algCase.name() + " est un doublon (ou déjà résolu)")
				.isTrue();
		}
		assertThat(stage.cases()).hasSize(expected);
	}

	@Test
	void pllCasesKeepTheTopOriented() {
		for (String puzzle : List.of("2x2", "3x3")) {
			for (AlgCase algCase : stage(puzzle, "pll").cases()) {
				Cube state = CaseStates.caseState(PUZZLES.get(puzzle).size(), algCase.algorithm());
				assertThat(CaseStates.topOriented(state)).as(algCase.name()).isTrue();
			}
		}
	}

	@Test
	void f2lGroupsMatchTheCaseCounts() {
		Map<String, Long> counts = stage("3x3", "f2l").cases()
			.stream()
			.collect(Collectors.groupingBy(AlgCase::group, Collectors.counting()));
		assertThat(counts).containsExactlyInAnyOrderEntriesOf(Map.of("Coin et arête en haut", 24L,
				"Coin en bas, arête en haut", 6L, "Coin en haut, arête en bas", 6L, "Coin et arête en bas", 5L));
	}

	@Test
	void ollGroupsMatchTheOrientedEdges() {
		for (AlgCase algCase : stage("3x3", "oll").cases()) {
			Face[] colors = CaseStates.caseState(3, algCase.algorithm()).colors();
			int edges = 0;
			for (int index : new int[] { 1, 3, 5, 7 }) {
				edges += (colors[index] == Face.U) ? 1 : 0;
			}
			int corners = 0;
			for (int index : new int[] { 0, 2, 6, 8 }) {
				corners += (colors[index] == Face.U) ? 1 : 0;
			}
			int expectedEdges = switch (algCase.group()) {
				case "Point" -> 0;
				case "Croix (OCLL)" -> 4;
				default -> 2;
			};
			assertThat(edges).as(algCase.name()).isEqualTo(expectedEdges);
			if (algCase.group().equals("Coins orientés")) {
				assertThat(corners).as(algCase.name()).isEqualTo(4);
			}
		}
	}

	@Test
	void pllGroupsMatchTheMovedPieces() {
		for (AlgCase algCase : stage("3x3", "pll").cases()) {
			int[] facelets = CaseStates.caseState(3, algCase.algorithm()).facelets();
			boolean cornersMoved = false;
			boolean edgesMoved = false;
			for (int i = 0; i < facelets.length; i++) {
				boolean corner = (i % 9) % 2 == 0 && i % 9 != 4;
				boolean edge = (i % 9) % 2 == 1;
				cornersMoved |= corner && facelets[i] != i;
				edgesMoved |= edge && facelets[i] != i;
			}
			switch (algCase.group()) {
				case "Arêtes" -> assertThat(cornersMoved).as(algCase.name()).isFalse();
				case "Coins" -> assertThat(edgesMoved).as(algCase.name()).isFalse();
				default -> assertThat(cornersMoved && edgesMoved).as(algCase.name()).isTrue();
			}
		}
	}

	@Test
	void twoByTwoAdjacentSwapHasHeadlightsOnTheLeft() {
		String algorithm = stage("2x2", "pll").cases().get(0).algorithm();
		Face[] colors = CaseStates.caseState(2, algorithm).colors();
		int left = Face.L.ordinal() * 4;
		assertThat(colors[left]).isEqualTo(colors[left + 1]);
	}

	@Test
	void ollParityFlipsExactlyOneDoubleEdge() {
		Cube state = CaseStates.caseState(4, stage("4x4", "parite-oll").cases().get(0).algorithm());
		assertThat(CaseStates.lowerLayersSolved(state, false)).isTrue();
		Face[] colors = state.colors();
		// ailes de la face U : UB (1, 2), UL (4, 8), UR (7, 11), UF (13, 14)
		int[] wings = { 1, 2, 4, 8, 7, 11, 13, 14 };
		int flipped = 0;
		for (int wing : wings) {
			flipped += (colors[wing] != Face.U) ? 1 : 0;
		}
		assertThat(flipped).isEqualTo(2);
		assertThat(colors[13]).isNotEqualTo(Face.U);
		assertThat(colors[14]).isNotEqualTo(Face.U);
	}

	@Test
	void pllParitySwapsFrontAndBackDoubleEdges() {
		Cube state = CaseStates.caseState(4, stage("4x4", "parite-pll").cases().get(0).algorithm());
		assertThat(CaseStates.lowerLayersSolved(state, false)).isTrue();
		assertThat(CaseStates.topOriented(state)).isTrue();
		Face[] colors = state.colors();
		for (int col : new int[] { 1, 2 }) {
			assertThat(colors[Face.F.ordinal() * 16 + col]).isEqualTo(Face.B);
			assertThat(colors[Face.B.ordinal() * 16 + col]).isEqualTo(Face.F);
		}
		for (Face side : new Face[] { Face.R, Face.L }) {
			for (int col = 0; col < 4; col++) {
				assertThat(colors[side.ordinal() * 16 + col]).isEqualTo(side);
			}
		}
	}

	@Test
	void edgeFlipTipFlipsFrontRightEdgeOnly() {
		// conseil de l'étape « Appariement des arêtes » vérifié sur 3x3
		int[] facelets = Cube.solved(3).apply("R U R' F R' F' R").facelets();
		int fr = Face.F.ordinal() * 9 + 5;
		int rf = Face.R.ordinal() * 9 + 3;
		assertThat(facelets[fr]).isEqualTo(rf);
		assertThat(facelets[rf]).isEqualTo(fr);
		int[][] otherEdges = { { Face.F.ordinal(), 3 }, { Face.L.ordinal(), 5 }, { Face.B.ordinal(), 3 },
				{ Face.B.ordinal(), 5 }, { Face.D.ordinal(), 1 }, { Face.D.ordinal(), 3 }, { Face.D.ordinal(), 5 },
				{ Face.D.ordinal(), 7 } };
		for (int[] edge : otherEdges) {
			int index = edge[0] * 9 + edge[1];
			assertThat(facelets[index]).isEqualTo(index);
		}
	}

}
