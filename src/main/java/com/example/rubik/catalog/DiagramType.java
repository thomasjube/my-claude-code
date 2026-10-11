package com.example.rubik.catalog;

/** Manière de représenter un cas. */
public enum DiagramType {

	/** Vue 3D (U, F, R) : seules les pièces des deux premières couches sont colorées. */
	F2L,

	/** Vue de dessus : seuls les autocollants jaunes sont colorés. */
	OLL,

	/** Vue de dessus en couleurs, avec les flèches de permutation. */
	PLL,

	/** Étape sans cas illustré (explications uniquement). */
	NONE

}
