package com.example.rubik.cube;

/**
 * Cube NxN modélisé par ses autocollants.
 *
 * <p>
 * Chaque autocollant est identifié par sa position d'origine (face et case à l'état résolu)
 * et possède une position courante : le centre de son cubie en coordonnées doublées (valeurs
 * de {@code -(n-1)} à {@code n-1} par pas de 2) et sa normale sortante. Un mouvement fait
 * pivoter les autocollants des tranches concernées.
 *
 * <p>
 * Dans chaque face, la case {@code (ligne, colonne)} suit la convention des patrons : U vu du
 * dessus avec F en bas, D vu du dessous avec F en haut, les faces latérales vues de face avec
 * U en haut.
 */
public final class Cube {

	private final int size;

	/** Centre du cubie (x, y, z) puis normale (x, y, z), pour chaque autocollant. */
	private final int[][] stickers;

	private Cube(int size, int[][] stickers) {
		this.size = size;
		this.stickers = stickers;
	}

	public static Cube solved(int size) {
		if (size < 2 || size > 7) {
			throw new IllegalArgumentException("Taille de cube non gérée : " + size);
		}
		int perFace = size * size;
		int[][] stickers = new int[6 * perFace][];
		for (Face face : Face.values()) {
			for (int row = 0; row < size; row++) {
				for (int col = 0; col < size; col++) {
					int[] center = cubieCenter(face, row, col, size);
					stickers[face.ordinal() * perFace + row * size + col] = new int[] { center[0], center[1],
							center[2], face.normal(0), face.normal(1), face.normal(2) };
				}
			}
		}
		return new Cube(size, stickers);
	}

	public int size() {
		return this.size;
	}

	public Cube copy() {
		int[][] copy = new int[this.stickers.length][];
		for (int i = 0; i < copy.length; i++) {
			copy[i] = this.stickers[i].clone();
		}
		return new Cube(this.size, copy);
	}

	public Cube apply(String notation) {
		return apply(Algorithm.parse(notation, this.size));
	}

	public Cube apply(Algorithm algorithm) {
		for (Move move : algorithm.moves()) {
			apply(move);
		}
		return this;
	}

	public Cube apply(Move move) {
		int axis = move.axis();
		for (int[] sticker : this.stickers) {
			if (move.affectsLayer((sticker[axis] + this.size - 1) / 2)) {
				for (int q = 0; q < move.quarterTurns(); q++) {
					rotateQuarter(sticker, 0, axis);
					rotateQuarter(sticker, 3, axis);
				}
			}
		}
		return this;
	}

	/** Quart de tour horaire vu depuis le côté positif de l'axe. */
	private static void rotateQuarter(int[] v, int offset, int axis) {
		int x = v[offset];
		int y = v[offset + 1];
		int z = v[offset + 2];
		switch (axis) {
			case 0 -> {
				v[offset + 1] = z;
				v[offset + 2] = -y;
			}
			case 1 -> {
				v[offset] = -z;
				v[offset + 2] = x;
			}
			default -> {
				v[offset] = y;
				v[offset + 1] = -x;
			}
		}
	}

	/**
	 * Pour chaque case (face, ligne, colonne), l'identifiant de l'autocollant qui s'y trouve.
	 * L'identifiant d'un autocollant est l'indice de sa case à l'état résolu.
	 */
	public int[] facelets() {
		int perFace = this.size * this.size;
		int[] facelets = new int[6 * perFace];
		for (int id = 0; id < this.stickers.length; id++) {
			int[] s = this.stickers[id];
			Face face = Face.fromNormal(s[3], s[4], s[5]);
			facelets[face.ordinal() * perFace + faceletIndex(face, s[0], s[1], s[2])] = id;
		}
		return facelets;
	}

	/** Face d'origine (donc couleur) de l'autocollant visible sur chaque case. */
	public Face[] colors() {
		int perFace = this.size * this.size;
		int[] facelets = facelets();
		Face[] colors = new Face[facelets.length];
		for (int i = 0; i < facelets.length; i++) {
			colors[i] = Face.values()[facelets[i] / perFace];
		}
		return colors;
	}

	/** Chaque case porte la couleur de sa face (les centres identiques sont interchangeables). */
	public boolean isSolved() {
		int perFace = this.size * this.size;
		Face[] colors = colors();
		for (int i = 0; i < colors.length; i++) {
			if (colors[i].ordinal() != i / perFace) {
				return false;
			}
		}
		return true;
	}

	/** Coordonnée (sur l'axe) du cubie qui porte, à l'état résolu, l'autocollant donné. */
	public int homeCoordinate(int stickerId, int axis) {
		int perFace = this.size * this.size;
		Face face = Face.values()[stickerId / perFace];
		int index = stickerId % perFace;
		return cubieCenter(face, index / this.size, index % this.size, this.size)[axis];
	}

	/** Coordonnée (sur l'axe) du cubie situé sous la case donnée. */
	public int positionCoordinate(int faceletIndex, int axis) {
		return homeCoordinate(faceletIndex, axis);
	}

	static int[] cubieCenter(Face face, int row, int col, int n) {
		int max = n - 1;
		int r = -max + 2 * row;
		int c = -max + 2 * col;
		return switch (face) {
			case U -> new int[] { c, max, r };
			case D -> new int[] { c, -max, -r };
			case F -> new int[] { c, -r, max };
			case B -> new int[] { -c, -r, -max };
			case R -> new int[] { max, -r, -c };
			case L -> new int[] { -max, -r, c };
		};
	}

	private int faceletIndex(Face face, int x, int y, int z) {
		int row;
		int col;
		switch (face) {
			case U -> {
				row = z;
				col = x;
			}
			case D -> {
				row = -z;
				col = x;
			}
			case F -> {
				row = -y;
				col = x;
			}
			case B -> {
				row = -y;
				col = -x;
			}
			case R -> {
				row = -y;
				col = -z;
			}
			default -> {
				row = -y;
				col = z;
			}
		}
		return index(row) * this.size + index(col);
	}

	private int index(int coordinate) {
		return (coordinate + this.size - 1) / 2;
	}

}
