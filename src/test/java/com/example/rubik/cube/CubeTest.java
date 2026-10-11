package com.example.rubik.cube;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CubeTest {

	private static Face color(Cube cube, Face face, int row, int col) {
		int n = cube.size();
		return cube.colors()[face.ordinal() * n * n + row * n + col];
	}

	@Test
	void uMovesFrontStickersToTheLeft() {
		Cube cube = Cube.solved(3).apply("U");
		for (int col = 0; col < 3; col++) {
			assertThat(color(cube, Face.L, 0, col)).isEqualTo(Face.F);
			assertThat(color(cube, Face.F, 0, col)).isEqualTo(Face.R);
		}
		assertThat(color(cube, Face.L, 1, 1)).isEqualTo(Face.L);
	}

	@Test
	void rMovesFrontStickersUp() {
		Cube cube = Cube.solved(3).apply("R");
		for (int row = 0; row < 3; row++) {
			assertThat(color(cube, Face.U, row, 2)).isEqualTo(Face.F);
			assertThat(color(cube, Face.B, row, 0)).isEqualTo(Face.U);
		}
	}

	@Test
	void fMovesUpStickersToTheRight() {
		Cube cube = Cube.solved(3).apply("F");
		for (int row = 0; row < 3; row++) {
			assertThat(color(cube, Face.R, row, 0)).isEqualTo(Face.U);
		}
		assertThat(color(cube, Face.U, 2, 0)).isEqualTo(Face.L);
	}

	@ParameterizedTest
	@ValueSource(ints = { 2, 3, 4 })
	void basicIdentities(int size) {
		assertThat(Cube.solved(size).apply("R R R R").isSolved()).isTrue();
		assertThat(Cube.solved(size).apply("R U R' U' ".repeat(6)).isSolved()).isTrue();
		if (size <= 3) {
			// ordre de (R U) : 15 sur 2x2, 105 sur 3x3
			assertThat(Cube.solved(size).apply("R U ".repeat(105)).isSolved()).isTrue();
		}
		assertThat(Cube.solved(size).apply("R U").isSolved()).isFalse();
		assertThat(Cube.solved(size).apply("x y z").isSolved()).isFalse();
	}

	@Test
	void inverseUndoesAlgorithm() {
		Algorithm alg = Algorithm.parse("Rw U2 x Rw U2 Rw U2 Rw' U2 Lw U2 3Rw' 2R2 Uw F' B2", 4);
		assertThat(Cube.solved(4).apply(alg).apply(alg.inverse()).isSolved()).isTrue();
	}

	@Test
	void wideAndSliceMovesAreConsistent() {
		assertThat(sameState(3, "r", "R M'")).isTrue();
		assertThat(sameState(3, "x", "R M' L'")).isTrue();
		assertThat(sameState(3, "y", "U E' D'")).isTrue();
		assertThat(sameState(3, "z", "F S B'")).isTrue();
		assertThat(sameState(4, "Rw", "R 2R")).isTrue();
		assertThat(sameState(4, "x", "Rw 2L' L'")).isTrue();
		assertThat(sameState(4, "r", "Rw")).isTrue();
	}

	@Test
	void rejectsInvalidNotation() {
		assertThatThrownBy(() -> Algorithm.parse("R Q", 3)).isInstanceOf(InvalidNotationException.class);
		assertThatThrownBy(() -> Algorithm.parse("M", 4)).isInstanceOf(InvalidNotationException.class);
		assertThatThrownBy(() -> Algorithm.parse("4R", 3)).isInstanceOf(InvalidNotationException.class);
	}

	private static boolean sameState(int size, String a, String b) {
		return java.util.Arrays.equals(Cube.solved(size).apply(a).facelets(), Cube.solved(size).apply(b).facelets());
	}

}
