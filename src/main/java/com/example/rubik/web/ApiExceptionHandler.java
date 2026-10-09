package com.example.rubik.web;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** Traduit les erreurs de saisie en réponses 400 (format Problem Details). */
@RestControllerAdvice
class ApiExceptionHandler {

	@ExceptionHandler(IllegalArgumentException.class)
	ProblemDetail badRequest(IllegalArgumentException ex) {
		ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, ex.getMessage());
		problem.setTitle("Requête invalide");
		return problem;
	}

}
