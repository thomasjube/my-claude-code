package com.example.rubik.catalog;

import com.example.rubik.cube.Algorithm;
import com.example.rubik.cube.Cube;
import com.example.rubik.cube.Face;

/**
 * Calculs sur les états « cas » : l'état d'un cas est obtenu en appliquant l'inverse de son
 * algorithme à un cube résolu, si bien que l'algorithme résout exactement cet état.
 */
public final class CaseStates {

	private static final String GRAY = "gray";

	private static final String[] AUF = { "", "U", "U2", "U'" };

	private CaseStates() {
	}

	public static Cube caseState(int size, String algorithm) {
		return Cube.solved(size).apply(Algorithm.parse(algorithm, size).inverse());
	}

	/** Mouvement d'ajustement de la face U pour {@code k} quarts de tour ({@code "", U, U2, U'}). */
	public static String auf(int quarterTurns) {
		return AUF[Math.floorMod(quarterTurns, 4)];
	}

	/**
	 * Vérifie que toutes les cases hors de la couche U ont la couleur de leur face, sauf
	 * éventuellement celles de la colonne avant-droite (emplacement FR) si
	 * {@code allowFrontRightSlot}. La comparaison se fait par couleur car, sur un 4x4, les
	 * centres d'une même couleur sont interchangeables.
	 */
	public static boolean lowerLayersSolved(Cube cube, boolean allowFrontRightSlot) {
		int n = cube.size();
		int perFace = n * n;
		Face[] colors = cube.colors();
		for (int i = 0; i < colors.length; i++) {
			if (cube.positionCoordinate(i, 1) == n - 1) {
				continue;
			}
			if (allowFrontRightSlot && cube.positionCoordinate(i, 0) == n - 1
					&& cube.positionCoordinate(i, 2) == n - 1) {
				continue;
			}
			if (colors[i].ordinal() != i / perFace) {
				return false;
			}
		}
		return true;
	}

	/** Toutes les cases de la face U portent la couleur de U. */
	public static boolean topOriented(Cube cube) {
		int perFace = cube.size() * cube.size();
		Face[] colors = cube.colors();
		for (int i = 0; i < perFace; i++) {
			if (colors[Face.U.ordinal() * perFace + i] != Face.U) {
				return false;
			}
		}
		return true;
	}

	/** Couleurs affichées pour chaque case, selon le masque du type de diagramme. */
	public static String[] maskedColors(Cube cube, DiagramType type) {
		int n = cube.size();
		int perFace = n * n;
		int[] facelets = cube.facelets();
		String[] colors = new String[facelets.length];
		for (int i = 0; i < facelets.length; i++) {
			int sticker = facelets[i];
			Face home = Face.values()[sticker / perFace];
			boolean visible = switch (type) {
				case F2L -> cube.homeCoordinate(sticker, 1) != n - 1;
				case OLL -> home == Face.U;
				case PLL, NONE -> true;
			};
			colors[i] = visible ? home.color() : GRAY;
		}
		return colors;
	}

	/**
	 * Signature d'un cas indépendante de l'AUF : minimum des vues masquées sur les
	 * ajustements de U avant l'algorithme (et après pour les PLL).
	 */
	public static String canonicalSignature(int size, String algorithm, DiagramType type) {
		Algorithm inverse = Algorithm.parse(algorithm, size).inverse();
		int postAufs = (type == DiagramType.PLL) ? 4 : 1;
		String best = null;
		for (int post = 0; post < postAufs; post++) {
			for (int pre = 0; pre < 4; pre++) {
				Cube cube = Cube.solved(size)
					.apply(Algorithm.parse(auf(-post), size))
					.apply(inverse)
					.apply(Algorithm.parse(auf(-pre), size));
				String signature = String.join(",", maskedColors(cube, type));
				if (best == null || signature.compareTo(best) < 0) {
					best = signature;
				}
			}
		}
		return best;
	}

	/**
	 * Emplacement de l'autocollant blanc (face D) du coin DFR dans l'état donné : face sur
	 * laquelle il se trouve et si le coin est dans la couche U.
	 */
	public static PiecePlace cornerPlace(Cube cube) {
		int n = cube.size();
		return place(cube, Face.D.ordinal() * n * n + (n - 1));
	}

	/** Emplacement de l'autocollant vert (face F) de l'arête FR d'un 3x3. */
	public static PiecePlace edgePlace(Cube cube) {
		return place(cube, Face.F.ordinal() * 9 + 5);
	}

	private static PiecePlace place(Cube cube, int stickerId) {
		int n = cube.size();
		int[] facelets = cube.facelets();
		for (int i = 0; i < facelets.length; i++) {
			if (facelets[i] == stickerId) {
				return new PiecePlace(Face.values()[i / (n * n)], cube.positionCoordinate(i, 1) == n - 1);
			}
		}
		throw new IllegalStateException("Autocollant introuvable : " + stickerId);
	}

	/**
	 * Position d'un autocollant.
	 *
	 * @param face face sur laquelle il se trouve
	 * @param top {@code true} si sa pièce est dans la couche U
	 */
	public record PiecePlace(Face face, boolean top) {
	}

}
