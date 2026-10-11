package com.example.rubik.web;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class ApiTest {

	@Autowired
	private MockMvc mockMvc;

	@Test
	void listsPuzzles() throws Exception {
		this.mockMvc.perform(get("/api/puzzles"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$[*].id").value(org.hamcrest.Matchers.contains("2x2", "3x3", "4x4")))
			.andExpect(jsonPath("$[1].stages[1].caseCount").value(41));
	}

	@Test
	void returnsPuzzleWithDiagrams() throws Exception {
		this.mockMvc.perform(get("/api/puzzles/3x3"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.stages[2].id").value("oll"))
			.andExpect(jsonPath("$.stages[2].cases.length()").value(57))
			.andExpect(jsonPath("$.stages[3].cases[0].diagram.faces.U.length()").value(9))
			.andExpect(jsonPath("$.stages[3].cases[0].diagram.arrows").isNotEmpty());
	}

	@Test
	void unknownPuzzleIs404() throws Exception {
		this.mockMvc.perform(get("/api/puzzles/5x5")).andExpect(status().isNotFound());
	}

	@Test
	void recognizesSune() throws Exception {
		// état résolu par la Sune (OLL 27)
		String body = """
				{"top": ["gray","yellow","gray","yellow","yellow","yellow","yellow","yellow","gray"],
				 "front": ["gray","gray","yellow"], "right": ["gray","gray","yellow"],
				 "back": ["gray","gray","yellow"], "left": ["gray","gray","gray"]}""";
		this.mockMvc
			.perform(post("/api/puzzles/3x3/stages/oll/recognize").contentType(MediaType.APPLICATION_JSON)
				.content(body))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.found").value(true))
			.andExpect(jsonPath("$.caseName").value("OLL 27"));
	}

	@Test
	void simulatesMoves() throws Exception {
		this.mockMvc.perform(get("/api/simulate").param("size", "3").param("moves", "R U R' U'"))
			.andExpect(status().isOk())
			.andExpect(jsonPath("$.moves.length()").value(4))
			.andExpect(jsonPath("$.frames.length()").value(5))
			.andExpect(jsonPath("$.solved").value(false));
		this.mockMvc.perform(get("/api/simulate").param("size", "4").param("moves", "M"))
			.andExpect(status().isBadRequest())
			.andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON));
	}

}
