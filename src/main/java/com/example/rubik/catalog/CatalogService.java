package com.example.rubik.catalog;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import com.example.rubik.catalog.CatalogViews.CaseView;
import com.example.rubik.catalog.CatalogViews.PuzzleSummary;
import com.example.rubik.catalog.CatalogViews.PuzzleView;
import com.example.rubik.catalog.CatalogViews.StageSummary;
import com.example.rubik.catalog.CatalogViews.StageView;
import com.example.rubik.cube.Algorithm;
import com.example.rubik.cube.Cube;
import com.example.rubik.cube.Face;

import org.springframework.stereotype.Service;

/** Catalogue des cubes, avec les diagrammes des cas précalculés au démarrage. */
@Service
public class CatalogService {

	private final List<Puzzle> puzzles;

	private final Map<String, PuzzleView> views = new LinkedHashMap<>();

	public CatalogService() {
		this(Catalog.puzzles());
	}

	CatalogService(List<Puzzle> puzzles) {
		this.puzzles = List.copyOf(puzzles);
		for (Puzzle puzzle : puzzles) {
			this.views.put(puzzle.id(), toView(puzzle));
		}
	}

	public List<PuzzleSummary> summaries() {
		return this.puzzles.stream()
			.map((puzzle) -> new PuzzleSummary(puzzle.id(), puzzle.name(), puzzle.size(), puzzle.summary(),
					puzzle.stages()
						.stream()
						.map((stage) -> new StageSummary(stage.id(), stage.title(), stage.cases().size()))
						.toList()))
			.toList();
	}

	public Optional<PuzzleView> view(String puzzleId) {
		return Optional.ofNullable(this.views.get(puzzleId));
	}

	public Optional<Puzzle> puzzle(String puzzleId) {
		return this.puzzles.stream().filter((puzzle) -> puzzle.id().equals(puzzleId)).findFirst();
	}

	private static PuzzleView toView(Puzzle puzzle) {
		List<StageView> stages = new ArrayList<>();
		for (Stage stage : puzzle.stages()) {
			List<CaseView> cases = new ArrayList<>();
			for (AlgCase algCase : stage.cases()) {
				Algorithm algorithm = Algorithm.parse(algCase.algorithm(), puzzle.size());
				int moveCount = (int) algorithm.moves()
					.stream()
					.filter((move) -> !move.notation().matches("[xyz].*"))
					.count();
				Cube state = Cube.solved(puzzle.size()).apply(algorithm.inverse());
				cases.add(new CaseView(algCase.id(), algCase.name(), algCase.group(), algCase.algorithm(), moveCount,
						algorithm.inverse().toString(), diagram(state, stage.diagramType())));
			}
			stages.add(new StageView(stage.id(), stage.title(), stage.summary(), stage.tips(), stage.diagramType(),
					stage.recognizable(), cases));
		}
		return new PuzzleView(puzzle.id(), puzzle.name(), puzzle.size(), puzzle.summary(), stages);
	}

	/** Diagramme d'un état, avec le masque correspondant au type. */
	public static Diagram diagram(Cube cube, DiagramType type) {
		int n = cube.size();
		int perFace = n * n;
		String[] colors = CaseStates.maskedColors(cube, type);
		Map<String, List<String>> faces = new LinkedHashMap<>();
		for (Face face : Face.values()) {
			int offset = face.ordinal() * perFace;
			faces.put(face.name(), List.of(colors).subList(offset, offset + perFace));
		}
		return new Diagram(type, n, faces, (type == DiagramType.PLL) ? arrows(cube) : List.of());
	}

	private static List<Diagram.Arrow> arrows(Cube cube) {
		int n = cube.size();
		int perFace = n * n;
		int[] facelets = cube.facelets();
		int[] target = new int[perFace];
		for (int i = 0; i < perFace; i++) {
			int sticker = facelets[Face.U.ordinal() * perFace + i];
			target[i] = (sticker / perFace == Face.U.ordinal()) ? sticker % perFace : i;
		}
		List<Diagram.Arrow> arrows = new ArrayList<>();
		for (int i = 0; i < perFace; i++) {
			int to = target[i];
			if (to == i) {
				continue;
			}
			boolean swap = target[to] == i;
			if (swap && to < i) {
				continue;
			}
			arrows.add(new Diagram.Arrow(new int[] { i / n, i % n }, new int[] { to / n, to % n }, swap));
		}
		return arrows;
	}

}
