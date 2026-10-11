package com.example.rubik.cube;

/**
 * Rotation d'un ensemble de tranches autour d'un axe.
 *
 * @param axis axe de rotation (0 = x, 1 = y, 2 = z)
 * @param layerMask bit {@code i} = tranche dont le centre vaut {@code -(n-1) + 2i} sur l'axe
 * @param quarterTurns nombre de quarts de tour horaires vus depuis le côté positif de l'axe (1 à 3)
 * @param notation notation d'origine du mouvement
 */
public record Move(int axis, long layerMask, int quarterTurns, String notation) {

	public Move {
		quarterTurns = Math.floorMod(quarterTurns, 4);
	}

	public Move inverse() {
		String inverted;
		if (this.notation.endsWith("2")) {
			inverted = this.notation;
		}
		else if (this.notation.endsWith("'")) {
			inverted = this.notation.substring(0, this.notation.length() - 1);
		}
		else {
			inverted = this.notation + "'";
		}
		return new Move(this.axis, this.layerMask, -this.quarterTurns, inverted);
	}

	boolean affectsLayer(int layerIndex) {
		return (this.layerMask & (1L << layerIndex)) != 0;
	}

}
