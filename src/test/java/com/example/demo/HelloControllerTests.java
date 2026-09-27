package com.example.demo;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(HelloController.class)
class HelloControllerTests {

	@Autowired
	private MockMvc mockMvc;

	@Test
	void helloWithDefaultName() throws Exception {
		mockMvc.perform(get("/hello"))
			.andExpect(status().isOk())
			.andExpect(content().string("Hello, World!"));
	}

	@Test
	void helloWithName() throws Exception {
		mockMvc.perform(get("/hello").param("name", "Thomas"))
			.andExpect(status().isOk())
			.andExpect(content().string("Hello, Thomas!"));
	}

}
