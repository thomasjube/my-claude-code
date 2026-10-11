package com.example.rubik.web;

import java.util.ArrayList;
import java.util.List;

import com.example.rubik.catalog.CatalogService;
import com.example.rubik.catalog.Diagram;
import com.example.rubik.catalog.DiagramType;
import com.example.rubik.cube.Algorithm;
import com.example.rubik.cube.Cube;
import com.example.rubik.cube.Move;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Applique une séquence de mouvements à un cube résolu. */
@RestController
public class SimulatorController {

	private static final int MAX_MOVES = 200;

	@GetMapping("/api/simulate")
	public Simulation simulate(@RequestParam(defaultValue = "3") int size,
			@RequestParam(defaultValue = "") String moves) {
		if (size < 2 || size > 4) {
			throw new IllegalArgumentException("Taille gérée : 2, 3 ou 4");
		}
		Algorithm algorithm = Algorithm.parse(moves, size);
		if (algorithm.length() > MAX_MOVES) {
			throw new IllegalArgumentException("Séquence trop longue (" + MAX_MOVES + " mouvements maximum)");
		}
		Cube cube = Cube.solved(size);
		List<Diagram> frames = new ArrayList<>();
		frames.add(CatalogService.diagram(cube, DiagramType.NONE));
		for (Move move : algorithm.moves()) {
			frames.add(CatalogService.diagram(cube.apply(move), DiagramType.NONE));
		}
		return new Simulation(size, algorithm.moves().stream().map(Move::notation).toList(), cube.isSolved(),
				frames);
	}

	/**
	 * @param size taille du cube
	 * @param moves mouvements interprétés
	 * @param solved {@code true} si le cube est résolu après la séquence
	 * @param frames couleurs des six faces avant le premier mouvement puis après chacun
	 */
	public record Simulation(int size, List<String> moves, boolean solved, List<Diagram> frames) {
	}

}
