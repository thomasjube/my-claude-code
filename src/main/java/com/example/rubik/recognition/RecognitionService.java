package com.example.rubik.recognition;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import com.example.rubik.catalog.AlgCase;
import com.example.rubik.catalog.CaseStates;
import com.example.rubik.catalog.DiagramType;
import com.example.rubik.catalog.Puzzle;
import com.example.rubik.catalog.Stage;
import com.example.rubik.cube.Algorithm;
import com.example.rubik.cube.Cube;
import com.example.rubik.cube.Face;

import org.springframework.stereotype.Service;

/**
 * Identifie un cas OLL ou PLL à partir des couleurs de la dernière couche.
 *
 * <p>
 * Pour chaque cas et chaque ajustement de U avant ({@code p}) et après ({@code q})
 * l'algorithme, l'état candidat est {@code résolu · U^-q · algo⁻¹ · U^-p} : c'est exactement
 * l'état que résout {@code U^p · algo · U^q}. On compare sa dernière couche à la saisie.
 */
@Service
public class RecognitionService {

	private static final String YELLOW = Face.U.color();

	/** Couleurs latérales dans l'ordre F, R, B, L : l'utilisateur peut tenir n'importe quel côté devant. */
	private static final List<String> SIDE_COLORS = List.of(Face.F.color(), Face.R.color(), Face.B.color(),
			Face.L.color());

	private static final Face[] SIDES = { Face.F, Face.R, Face.B, Face.L };

	public Recognition recognize(Puzzle puzzle, Stage stage, LastLayerInput input) {
		if (!stage.recognizable()) {
			throw new IllegalArgumentException("L'identification n'est pas disponible pour l'étape « " + stage.title() + " »");
		}
		int n = puzzle.size();
		List<String> observed = flatten(input, n);
		boolean oll = stage.diagramType() == DiagramType.OLL;
		if (!oll && observed.subList(0, n * n).stream().anyMatch((color) -> !YELLOW.equals(color))) {
			return Recognition.notFound("La face du haut doit être entièrement jaune : terminez d'abord l'OLL.");
		}
		List<AlgCase> candidates = new ArrayList<>();
		candidates.add(null);
		candidates.addAll(stage.cases());
		int postAufs = oll ? 1 : 4;
		// décalage 0 d'abord (vert devant) : l'ajustement final est alors exact
		int shifts = oll ? 1 : 4;
		for (int shift = 0; shift < shifts; shift++) {
			for (AlgCase algCase : candidates) {
				String notation = (algCase != null) ? algCase.algorithm() : "";
				Algorithm inverse = Algorithm.parse(notation, n).inverse();
				for (int post = 0; post < postAufs; post++) {
					for (int pre = 0; pre < 4; pre++) {
						Cube state = Cube.solved(n)
							.apply(Algorithm.parse(CaseStates.auf(-post), n))
							.apply(inverse)
							.apply(Algorithm.parse(CaseStates.auf(-pre), n));
						if (matches(flatten(state, n), observed, oll, shift)) {
							// sans algorithme, les deux ajustements se cumulent
							return (algCase != null)
									? result(algCase, CaseStates.auf(pre), CaseStates.auf(post), oll, shift != 0)
									: result(null, "", CaseStates.auf(pre + post), oll, shift != 0);
						}
					}
				}
			}
		}
		return Recognition.notFound(oll
				? "Motif non reconnu : vérifiez les autocollants jaunes (les deux premières couches doivent être résolues)."
				: "Permutation non reconnue : vérifiez les couleurs saisies (un cas impossible indique une erreur de saisie).");
	}

	/**
	 * @param rotatedHold les couleurs ne correspondent qu'en supposant le cube tenu avec un
	 * autre côté que le vert devant : l'ajustement final ne peut alors pas être calculé
	 */
	private static Recognition result(AlgCase algCase, String preAuf, String exactPostAuf, boolean oll,
			boolean rotatedHold) {
		String postAuf = rotatedHold ? "" : exactPostAuf;
		String finish = rotatedHold ? " Terminez en tournant U pour aligner la dernière couche." : "";
		if (algCase == null) {
			String message = oll ? "La face jaune est déjà faite : passez à la PLL."
					: rotatedHold ? "La dernière couche est résolue : tournez U pour l'aligner."
							: postAuf.isEmpty() ? "La dernière couche est déjà résolue !"
									: "La dernière couche est résolue à un tour près : faites " + postAuf + ".";
			return new Recognition(true, message, null, null, "", "", postAuf, postAuf);
		}
		String solution = Stream.of(preAuf, algCase.algorithm(), postAuf)
			.filter((part) -> !part.isEmpty())
			.collect(Collectors.joining(" "));
		String message = "Cas reconnu : " + algCase.name()
				+ (preAuf.isEmpty() ? "." : " (faites d'abord " + preAuf + ").") + finish;
		return new Recognition(true, message, algCase.id(), algCase.name(), preAuf, algCase.algorithm(), postAuf,
				solution);
	}

	/** Dernière couche d'un état : face U puis ligne du haut de F, R, B, L. */
	private static List<String> flatten(Cube cube, int n) {
		Face[] colors = cube.colors();
		List<String> result = new ArrayList<>();
		for (int i = 0; i < n * n; i++) {
			result.add(colors[Face.U.ordinal() * n * n + i].color());
		}
		for (Face side : SIDES) {
			for (int col = 0; col < n; col++) {
				result.add(colors[side.ordinal() * n * n + col].color());
			}
		}
		return result;
	}

	private static List<String> flatten(LastLayerInput input, int n) {
		check(input.top(), n * n, "top");
		List<String> result = new ArrayList<>(input.top());
		for (Object[] side : new Object[][] { { input.front(), "front" }, { input.right(), "right" },
				{ input.back(), "back" }, { input.left(), "left" } }) {
			@SuppressWarnings("unchecked")
			List<String> colors = (List<String>) side[0];
			check(colors, n, (String) side[1]);
			result.addAll(colors);
		}
		return result.stream().map((color) -> color.toLowerCase().trim()).toList();
	}

	private static void check(List<String> colors, int expected, String name) {
		if (colors == null || colors.size() != expected || colors.stream().anyMatch((color) -> color == null)) {
			throw new IllegalArgumentException("« " + name + " » doit contenir " + expected + " couleurs");
		}
	}

	private static boolean matches(List<String> expected, List<String> observed, boolean oll, int shift) {
		if (oll) {
			for (int i = 0; i < expected.size(); i++) {
				if (YELLOW.equals(expected.get(i)) != YELLOW.equals(observed.get(i))) {
					return false;
				}
			}
			return true;
		}
		return matchesWithShift(expected, observed, shift);
	}

	/** Compare en décalant les couleurs latérales (cube tenu avec un autre côté devant). */
	private static boolean matchesWithShift(List<String> expected, List<String> observed, int shift) {
		for (int i = 0; i < expected.size(); i++) {
			String color = expected.get(i);
			int index = SIDE_COLORS.indexOf(color);
			if (index >= 0) {
				color = SIDE_COLORS.get((index + shift) % 4);
			}
			if (!color.equals(observed.get(i))) {
				return false;
			}
		}
		return true;
	}

}
