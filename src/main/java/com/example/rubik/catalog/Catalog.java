package com.example.rubik.catalog;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import com.example.rubik.cube.Cube;

/** Données : cubes, étapes et algorithmes. */
public final class Catalog {

	private Catalog() {
	}

	public static List<Puzzle> puzzles() {
		return List.of(twoByTwo(), threeByThree(), fourByFour());
	}

	// ----------------------------------------------------------------------------- 3x3

	static final String[] F2L = {
			"U R U' R'", "U' F' U F", "F' U' F", "R U R'",
			"U' R U R' U2 R U' R'", "U F' U' F U2 F' U F", "U' R U2 R' U2 R U' R'", "U F' U2 F U2 F' U F",
			"U' R U' R' U F' U' F", "U' R U R' U R U R'", "U' R U2 R' U F' U' F", "R U' R' U R U' R' U2 R U' R'",
			"U F' U F U' F' U' F", "U' R U' R' U R U R'", "R' D' R U' R' D R U R U' R'", "R U' R' U2 F' U' F",
			"R U2 R' U' R U R'", "F' U2 F U F' U' F", "U R U2 R' U R U' R'", "U' F' U2 F U' F' U F",
			"U2 R U R' U R U' R'", "U2 F' U' F U' F' U F", "U R U' R' U' R U' R' U R U' R'",
			"F U R U' R' F' R U' R'", "U' R' F R F' R U R'", "U R U' R' F R' F' R", "R U' R' U R U' R'",
			"F' U F U' F' U F", "R' F R F' R U' R' U R U' R' U2 R U' R'", "R U R' U' R U R'",
			"U' R' F R F' R U' R'", "U R U' R' U R U' R' U R U' R'", "U' R U' R' U2 R U' R'",
			"U R U R' U2 R U R'", "U2 R U' R' U' F' U' F", "R U F R U R' U' F' R'", "R U' R' F' U' F",
			"R U' R' U' R U R' U2 R U' R'", "R U' R' U R U2 R' U R U' R'", "F' U' F U R U' R'",
			"R F U R U' R' F' U' R'" };

	static final String[][] OLL = {
			{ "1", "Point", "R U2 R2 F R F' U2 R' F R F'" },
			{ "2", "Point", "F R U R' U' F' f R U R' U' f'" },
			{ "3", "Point", "f R U R' U' f' U' F R U R' U' F'" },
			{ "4", "Point", "f R U R' U' f' U F R U R' U' F'" },
			{ "5", "Carré", "r' U2 R U R' U r" },
			{ "6", "Carré", "r U2 R' U' R U' r'" },
			{ "7", "Petit éclair", "r U R' U R U2 r'" },
			{ "8", "Petit éclair", "r' U' R U' R' U2 r" },
			{ "9", "Poisson", "R U R' U' R' F R2 U R' U' F'" },
			{ "10", "Poisson", "R U R' U R' F R F' R U2 R'" },
			{ "11", "Petit éclair", "r U R' U R' F R F' R U2 r'" },
			{ "12", "Petit éclair", "M' R' U' R U' R' U2 R U' M" },
			{ "13", "Cavalier", "F U R U' R2 F' R U R U' R'" },
			{ "14", "Cavalier", "R' F R U R' F' R F U' F'" },
			{ "15", "Cavalier", "r' U' r R' U' R U r' U r" },
			{ "16", "Cavalier", "r U r' R U R' U' r U' r'" },
			{ "17", "Point", "R U R' U R' F R F' U2 R' F R F'" },
			{ "18", "Point", "r U R' U R U2 r2 U' R U' R' U2 r" },
			{ "19", "Point", "M U R U R' U' M' R' F R F'" },
			{ "20", "Point", "r U R' U' M2 U R U' R' U' M'" },
			{ "21", "Croix (OCLL)", "R U2 R' U' R U R' U' R U' R'" },
			{ "22", "Croix (OCLL)", "R U2 R2 U' R2 U' R2 U2 R" },
			{ "23", "Croix (OCLL)", "R2 D' R U2 R' D R U2 R" },
			{ "24", "Croix (OCLL)", "r U R' U' r' F R F'" },
			{ "25", "Croix (OCLL)", "F' r U R' U' r' F R" },
			{ "26", "Croix (OCLL)", "R U2 R' U' R U' R'" },
			{ "27", "Croix (OCLL)", "R U R' U R U2 R'" },
			{ "28", "Coins orientés", "r U R' U' M U R U' R'" },
			{ "29", "Forme bizarre", "R U R' U' R U' R' F' U' F R U R'" },
			{ "30", "Forme bizarre", "F R' F R2 U' R' U' R U R' F2" },
			{ "31", "P", "R' U' F U R U' R' F' R" },
			{ "32", "P", "L U F' U' L' U L F L'" },
			{ "33", "T", "R U R' U' R' F R F'" },
			{ "34", "C", "R U R2 U' R' F R U R U' F'" },
			{ "35", "Poisson", "R U2 R2 F R F' R U2 R'" },
			{ "36", "W", "L' U' L U' L' U L U L F' L' F" },
			{ "37", "Poisson", "F R' F' R U R U' R'" },
			{ "38", "W", "R U R' U R U' R' U' R' F R F'" },
			{ "39", "Grand éclair", "L F' L' U' L U F U' L'" },
			{ "40", "Grand éclair", "R' F R U R' U' F' U R" },
			{ "41", "Forme bizarre", "R U R' U R U2 R' F R U R' U' F'" },
			{ "42", "Forme bizarre", "R' U' R U' R' U2 R F R U R' U' F'" },
			{ "43", "P", "F' U' L' U L F" },
			{ "44", "P", "F U R U' R' F'" },
			{ "45", "T", "F R U R' U' F'" },
			{ "46", "C", "R' U' R' F R F' U R" },
			{ "47", "L", "R' U' R' F R F' R' F R F' U R" },
			{ "48", "L", "F R U R' U' R U R' U' F'" },
			{ "49", "L", "r U' r2 U r2 U r2 U' r" },
			{ "50", "L", "r' U r2 U' r2 U' r2 U r'" },
			{ "51", "Ligne", "F U R U' R' U R U' R' F'" },
			{ "52", "Ligne", "R U R' U R U' B U' B' R'" },
			{ "53", "L", "r' U' R U' R' U R U' R' U2 r" },
			{ "54", "L", "r U R' U R U' R' U R U2 r'" },
			{ "55", "Ligne", "R' F R U R U' R2 F' R2 U' R' U R U R'" },
			{ "56", "Ligne", "r' U' r U' R' U R U' R' U R r' U r" },
			{ "57", "Coins orientés", "R U R' U' M' U R U' r'" } };

	static final String[][] PLL = {
			{ "Ua", "Arêtes", "M2 U M U2 M' U M2" },
			{ "Ub", "Arêtes", "M2 U' M U2 M' U' M2" },
			{ "H", "Arêtes", "M2 U M2 U2 M2 U M2" },
			{ "Z", "Arêtes", "M2 U M2 U M' U2 M2 U2 M' U2" },
			{ "Aa", "Coins", "R' F R' B2 R F' R' B2 R2" },
			{ "Ab", "Coins", "R2 B2 R F R' B2 R F' R" },
			{ "E", "Coins", "x' R U' R' D R U R' D' R U R' D R U' R' D' x" },
			{ "T", "Échange de coins adjacents", "R U R' U' R' F R2 U' R' U' R U R' F'" },
			{ "F", "Échange de coins adjacents", "R' U' F' R U R' U' R' F R2 U' R' U' R U R' U R" },
			{ "Ja", "Échange de coins adjacents", "R' U L' U2 R U' R' U2 R L" },
			{ "Jb", "Échange de coins adjacents", "R U R' F' R U R' U' R' F R2 U' R'" },
			{ "Ra", "Échange de coins adjacents", "R U' R' U' R U R D R' U' R D' R' U2 R'" },
			{ "Rb", "Échange de coins adjacents", "R2 F R U R U' R' F' R U2 R' U2 R" },
			{ "Ga", "Échange de coins adjacents", "R2 U R' U R' U' R U' R2 U' D R' U R D'" },
			{ "Gb", "Échange de coins adjacents", "R' U' R U D' R2 U R' U R U' R U' R2 D" },
			{ "Gc", "Échange de coins adjacents", "R2 U' R U' R U R' U R2 U D' R U' R' D" },
			{ "Gd", "Échange de coins adjacents", "R U R' U' D R2 U' R U' R' U R' U R2 D'" },
			{ "V", "Échange de coins opposés", "R' U R' U' B' R' B2 U' B' U B' R B R" },
			{ "Y", "Échange de coins opposés", "F R U' R' U' R U R' F' R U R' U' R' F R F'" },
			{ "Na", "Échange de coins opposés", "R U R' U R U R' F' R U R' U' R' F R2 U' R' U2 R U' R'" },
			{ "Nb", "Échange de coins opposés", "R' U R U' R' F' U' F R U R' F R' F' R U' R" } };

	private static Puzzle threeByThree() {
		Stage cross = new Stage("croix", "Croix", """
				Première étape de la méthode CFOP (Fridrich) : placer les quatre arêtes blanches \
				autour du centre blanc, alignées avec les centres latéraux. Elle se fait de façon \
				intuitive, idéalement en 8 mouvements maximum et en la construisant sur la face D.""",
				List.of("Cherchez chaque arête blanche et amenez-la en face de son centre avant de la descendre.",
						"Entraînez-vous à faire la croix en bas (blanc sur D) pour voir plus vite les paires F2L.",
						"Une arête blanche de la couche du haut, alignée avec son centre, se descend d'un demi-tour (F2, R2...)."),
				DiagramType.NONE, false, List.of());
		Stage f2l = new Stage("f2l", "F2L", """
				First Two Layers : on insère simultanément un coin blanc et l'arête correspondante \
				dans chacun des quatre emplacements. Les 41 cas sont présentés pour l'emplacement \
				avant-droit (FR) ; pour un autre emplacement, tournez le cube (y, y', y2).""",
				List.of("Commencez par comprendre les cas de base (paire formée en haut) : les autres s'y ramènent.",
						"Repérez la paire suivante pendant que vous insérez la précédente (look-ahead).",
						"Les pièces grises appartiennent à la dernière couche : elles n'ont pas d'importance ici."),
				DiagramType.F2L, false, f2lCases());
		Stage oll = new Stage("oll", "OLL", """
				Orientation of the Last Layer : 57 algorithmes pour rendre toute la face jaune en une \
				seule étape. En 2-look : orienter d'abord les arêtes (OLL 45, 44 puis 33) pour obtenir \
				la croix jaune, puis les coins avec les 7 cas « Croix (OCLL) ».""",
				List.of("Apprenez d'abord les 7 cas OCLL (21 à 27) et les 3 algorithmes de croix : c'est l'OLL en 2 temps.",
						"Seuls les autocollants jaunes sont colorés : reconnaissez le cas au motif du dessus et des côtés.",
						"Utilisez « Identifier mon cas » pour trouver l'algorithme et l'ajustement (AUF) à faire avant."),
				DiagramType.OLL, true, cases("oll", "OLL ", OLL));
		Stage pll = new Stage("pll", "PLL", """
				Permutation of the Last Layer : 21 algorithmes pour placer les pièces de la dernière \
				couche. Les flèches indiquent où chaque pièce doit aller. En 2-look : permuter les \
				coins (T ou Y), puis les arêtes (Ua, Ub, H ou Z).""",
				List.of("Reconnaissez le cas avec les « phares » (deux coins de même couleur sur un côté) et les blocs formés.",
						"Pour la PLL en 2 temps, apprenez T, Y (coins) puis Ua, Ub, H et Z (arêtes).",
						"Un dernier mouvement de U (AUF) peut être nécessaire après l'algorithme."),
				DiagramType.PLL, true, cases("pll", "", PLL));
		return new Puzzle("3x3", "Cube 3x3", 3, """
				Méthode CFOP : croix, F2L, OLL puis PLL. Tenez le cube jaune en haut et vert \
				devant : tous les algorithmes et diagrammes utilisent cette orientation.""",
				List.of(cross, f2l, oll, pll));
	}

	private static Puzzle twoByTwo() {
		Stage firstLayer = new Stage("premiere-couche", "Première couche", """
				Formez la face blanche avec ses coins bien placés (les couleurs latérales doivent \
				correspondre deux à deux). Chaque coin s'insère dans l'emplacement avant-droit avec \
				l'un des cas ci-dessous.""",
				List.of("Tenez la face blanche en bas et placez le coin à insérer au-dessus de son emplacement (UFR).",
						"Sur un 2x2 il n'y a pas de centres : choisissez un premier coin comme référence.",
						"Les pièces grises (couche du haut) n'ont pas d'importance à cette étape."),
				DiagramType.F2L, false, firstLayerCases());
		Stage oll = new Stage("oll", "OLL", """
				Orienter les coins de la dernière couche pour obtenir la face jaune : 7 cas, les \
				mêmes que les OCLL du 3x3.""",
				List.of("Sune et Anti-Sune suffisent pour tout résoudre en les répétant, mais les 7 algorithmes sont plus rapides.",
						"Seuls les autocollants jaunes sont colorés sur les diagrammes."),
				DiagramType.OLL, true, cases("oll", "", new String[][] {
						{ "Sune", "OLL", "R U R' U R U2 R'" },
						{ "Anti-Sune", "OLL", "R U2 R' U' R U' R'" },
						{ "H", "OLL", "R U2 R' U' R U R' U' R U' R'" },
						{ "Pi", "OLL", "R U2 R2 U' R2 U' R2 U2 R" },
						{ "U (phares)", "OLL", "R2 D' R U2 R' D R U2 R" },
						{ "T", "OLL", "R U R' U' R' F R F'" },
						{ "L (nœud papillon)", "OLL", "F R' F' R U R U' R'" } }));
		Stage pll = new Stage("pll", "PLL", """
				Permuter les coins de la dernière couche : deux coins adjacents à échanger (un côté \
				a des « phares ») ou deux coins opposés (aucun côté n'a de phares).""",
				List.of("Coins adjacents : placez les phares à gauche (face L) avant l'algorithme.",
						"Aucun phare : l'algorithme des coins opposés s'applique directement.",
						"Finissez par un mouvement de U, puis éventuellement de D si la couche du bas est décalée."),
				DiagramType.PLL, true, cases("pll", "", new String[][] {
						{ "Coins adjacents", "PLL", "R U R' U' R' F R2 U' R' U' R U R' F'" },
						{ "Coins opposés", "PLL", "F R U' R' U' R U R' F' R U R' U' R' F R F'" } }));
		return new Puzzle("2x2", "Cube 2x2", 2, """
				Méthode par couches (Ortega simplifiée) : première couche, orientation (OLL) puis \
				permutation (PLL) des coins du haut. Jaune en haut, vert devant.""",
				List.of(firstLayer, oll, pll));
	}

	private static Puzzle fourByFour() {
		Stage centers = new Stage("centres", "Centres", """
				Méthode de réduction : on ramène le 4x4 à un 3x3. Première étape : assembler les \
				blocs 2x2 de centres de chaque couleur.""",
				List.of("Faites d'abord deux centres opposés (blanc puis jaune) avec des mouvements de tranches (Rw, 2R).",
						"Construisez ensuite les quatre centres restants par barres de 1x2, sans casser les deux premiers.",
						"Respectez l'ordre des couleurs du 3x3 : avec jaune en haut et vert devant, l'orange est à droite."),
				DiagramType.NONE, false, List.of());
		Stage edges = new Stage("aretes", "Appariement des arêtes", """
				Associez les deux ailes de chaque arête pour former 12 « arêtes doubles ». Méthode \
				3-2-3 : placez deux ailes assorties en face l'une de l'autre sur les faces F, \
				tournez une tranche (Uw ou Dw), remplacez l'arête appariée puis rétablissez la tranche.""",
				List.of("Appariez 8 arêtes en les rangeant sur U et D, puis finissez les 4 dernières sur la couche du milieu.",
						"R U R' F R' F' R retourne l'arête FR sur place sans toucher aux autres arêtes du milieu ni du bas."),
				DiagramType.NONE, false, List.of());
		Stage threeByThree = new Stage("3x3", "Résolution comme un 3x3", """
				Une fois centres et arêtes réunis, le 4x4 se résout comme un 3x3 : croix, F2L, OLL \
				et PLL (voir l'onglet 3x3). Deux situations impossibles sur un 3x3 peuvent alors \
				apparaître : les parités.""",
				List.of("N'utilisez que des mouvements de faces extérieures (R, U...) ou larges complets pour ne pas casser les centres.",
						"Les tranches M, E, S n'existent pas sur un 4x4 : les algorithmes du 3x3 qui les utilisent sont à adapter."),
				DiagramType.NONE, false, List.of());
		Stage ollParity = new Stage("parite-oll", "Parité OLL", """
				Pendant l'OLL, un nombre impair d'arêtes est mal orienté (une seule arête retournée). \
				L'algorithme ci-dessous retourne l'arête double UF ; il modifie aussi la permutation \
				de la dernière couche, ce qui est sans conséquence puisque la PLL suit.""",
				List.of("Placez l'arête retournée devant (UF), jaune tourné vers vous, puis faites l'algorithme.",
						"Enchaînez ensuite avec l'OLL normale."),
				DiagramType.PLL, false, List.of(new AlgCase("parite-oll", "Parité OLL", "Parité",
						"Rw U2 x Rw U2 Rw U2 Rw' U2 Lw U2 Rw' U2 Rw U2 Rw' U2 Rw'")));
		Stage pllParity = new Stage("parite-pll", "Parité PLL", """
				En PLL, deux arêtes doubles opposées sont échangées (ou un cas de PLL impossible sur \
				3x3 apparaît). L'algorithme ci-dessous échange les arêtes UF et UB.""",
				List.of("2R désigne uniquement la deuxième tranche depuis la droite ; Uw les deux couches du haut.",
						"Le U2 final n'est qu'un ajustement de la face du haut (AUF).",
						"Si deux coins sont aussi à échanger, faites d'abord une PLL de coins, puis cet algorithme."),
				DiagramType.PLL, false, List.of(new AlgCase("parite-pll", "Parité PLL", "Parité",
						"2R2 U2 2R2 Uw2 2R2 Uw2 U2")));
		return new Puzzle("4x4", "Cube 4x4", 4, """
				Méthode de réduction : centres, appariement des arêtes, puis résolution comme un \
				3x3 avec, si besoin, les algorithmes de parité. Jaune en haut, vert devant.""",
				List.of(centers, edges, threeByThree, ollParity, pllParity));
	}

	private static final List<String> F2L_GROUPS = List.of("Coin et arête en haut", "Coin en bas, arête en haut",
			"Coin en haut, arête en bas", "Coin et arête en bas");

	/** Cas F2L regroupés selon la position du coin et de l'arête, puis numérotés. */
	private static List<AlgCase> f2lCases() {
		List<String[]> rows = new ArrayList<>();
		for (String algorithm : F2L) {
			Cube state = CaseStates.caseState(3, algorithm);
			boolean cornerTop = CaseStates.cornerPlace(state).top();
			boolean edgeTop = CaseStates.edgePlace(state).top();
			int group = cornerTop ? (edgeTop ? 0 : 2) : (edgeTop ? 1 : 3);
			rows.add(new String[] { F2L_GROUPS.get(group), algorithm });
		}
		rows.sort(Comparator.comparingInt((String[] row) -> F2L_GROUPS.indexOf(row[0])));
		List<AlgCase> cases = new ArrayList<>();
		for (int i = 0; i < rows.size(); i++) {
			cases.add(new AlgCase("f2l-" + (i + 1), "F2L " + (i + 1), rows.get(i)[0], rows.get(i)[1]));
		}
		return cases;
	}

	private static List<AlgCase> firstLayerCases() {
		String[] algorithms = { "R U R'", "F' U' F", "R U2 R' U' R U R'", "R U R' U' R U R'", "R U' R' U R U' R'" };
		List<AlgCase> cases = new ArrayList<>();
		for (int i = 0; i < algorithms.length; i++) {
			CaseStates.PiecePlace white = CaseStates.cornerPlace(CaseStates.caseState(2, algorithms[i]));
			String direction = switch (white.face()) {
				case U -> "blanc vers le haut";
				case R -> "blanc vers la droite";
				default -> "blanc vers l'avant";
			};
			String group = white.top() ? "Coin en haut" : "Coin en bas, mal orienté";
			String name = (white.top() ? "Coin en haut, " : "Coin en bas, ") + direction;
			cases.add(new AlgCase("premiere-couche-" + (i + 1), name, group, algorithms[i]));
		}
		return cases;
	}

	private static List<AlgCase> cases(String prefix, String namePrefix, String[][] rows) {
		List<AlgCase> cases = new ArrayList<>();
		for (String[] row : rows) {
			String slug = row[0].toLowerCase().replaceAll("[^a-z0-9]+", "-").replaceAll("(^-|-$)", "");
			cases.add(new AlgCase(prefix + "-" + slug, namePrefix + row[0], row[1], row[2]));
		}
		return cases;
	}

}
