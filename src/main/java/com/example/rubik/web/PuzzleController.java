package com.example.rubik.web;

import java.util.List;

import com.example.rubik.catalog.CatalogService;
import com.example.rubik.catalog.CatalogViews.PuzzleSummary;
import com.example.rubik.catalog.CatalogViews.PuzzleView;
import com.example.rubik.catalog.Puzzle;
import com.example.rubik.catalog.Stage;
import com.example.rubik.recognition.LastLayerInput;
import com.example.rubik.recognition.Recognition;
import com.example.rubik.recognition.RecognitionService;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/puzzles")
public class PuzzleController {

	private final CatalogService catalog;

	private final RecognitionService recognition;

	public PuzzleController(CatalogService catalog, RecognitionService recognition) {
		this.catalog = catalog;
		this.recognition = recognition;
	}

	@GetMapping
	public List<PuzzleSummary> puzzles() {
		return this.catalog.summaries();
	}

	@GetMapping("/{puzzleId}")
	public PuzzleView puzzle(@PathVariable String puzzleId) {
		return this.catalog.view(puzzleId).orElseThrow(() -> notFound("Cube inconnu : " + puzzleId));
	}

	@PostMapping("/{puzzleId}/stages/{stageId}/recognize")
	public Recognition recognize(@PathVariable String puzzleId, @PathVariable String stageId,
			@RequestBody LastLayerInput input) {
		Puzzle puzzle = this.catalog.puzzle(puzzleId).orElseThrow(() -> notFound("Cube inconnu : " + puzzleId));
		Stage stage = puzzle.stage(stageId).orElseThrow(() -> notFound("Étape inconnue : " + stageId));
		return this.recognition.recognize(puzzle, stage, input);
	}

	private static ResponseStatusException notFound(String message) {
		return new ResponseStatusException(HttpStatus.NOT_FOUND, message);
	}

}
