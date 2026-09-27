package com.example.rubik.cube;

/** Levée lorsqu'une séquence de mouvements ne peut pas être interprétée. */
public class InvalidNotationException extends IllegalArgumentException {

	public InvalidNotationException(String message) {
		super(message);
	}

}
