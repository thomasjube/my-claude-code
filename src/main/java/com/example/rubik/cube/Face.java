package com.example.rubik.cube;

/**
 * Faces du cube, dans l'orientation de résolution CFOP : jaune en haut, vert devant.
 * Repère : x vers la droite (R), y vers le haut (U), z vers l'avant (F).
 */
public enum Face {

	U(0, 1, 0, "yellow"),
	R(1, 0, 0, "orange"),
	F(0, 0, 1, "green"),
	D(0, -1, 0, "white"),
	L(-1, 0, 0, "red"),
	B(0, 0, -1, "blue");

	private final int[] normal;

	private final String color;

	Face(int x, int y, int z, String color) {
		this.normal = new int[] { x, y, z };
		this.color = color;
	}

	/** Composante de la normale sortante sur l'axe donné (0 = x, 1 = y, 2 = z). */
	public int normal(int axis) {
		return this.normal[axis];
	}

	/** Couleur de la face à l'état résolu. */
	public String color() {
		return this.color;
	}

	static Face fromNormal(int x, int y, int z) {
		for (Face face : values()) {
			if (face.normal[0] == x && face.normal[1] == y && face.normal[2] == z) {
				return face;
			}
		}
		throw new IllegalStateException("Normale invalide : " + x + "," + y + "," + z);
	}

}
