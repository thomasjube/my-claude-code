package com.example.rubik.cube;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Séquence de mouvements en notation standard (WCA / SiGN) pour un cube de taille donnée.
 *
 * <ul>
 * <li>{@code R U F L D B} : une face extérieure ; {@code 2R} : deuxième tranche seule</li>
 * <li>{@code Rw} ou {@code r} : deux tranches extérieures ; {@code 3Rw} : trois tranches</li>
 * <li>{@code M E S} : tranches du milieu (tailles impaires) ; {@code x y z} : rotations du cube</li>
 * <li>suffixes {@code '} (anti-horaire), {@code 2} (demi-tour)</li>
 * </ul>
 */
public record Algorithm(List<Move> moves) {

	private static final Pattern TOKEN = Pattern
		.compile("(\\d+)?([URFDLB])(w)?|([urfdlb])|([MES])|([xyz])");

	public Algorithm {
		moves = List.copyOf(moves);
	}

	public static Algorithm parse(String notation, int size) {
		List<Move> moves = new ArrayList<>();
		String cleaned = notation.replace('’', '\'').replace('′', '\'').replaceAll("[()\\[\\]]", " ").trim();
		if (cleaned.isEmpty()) {
			return new Algorithm(moves);
		}
		for (String token : cleaned.split("\\s+")) {
			moves.add(parseToken(token, size));
		}
		return new Algorithm(moves);
	}

	private static Move parseToken(String token, int size) {
		String body = token;
		int turns = 1;
		if (body.endsWith("2'")) {
			turns = 2;
			body = body.substring(0, body.length() - 2);
		}
		else if (body.endsWith("'")) {
			turns = -1;
			body = body.substring(0, body.length() - 1);
		}
		else if (body.endsWith("2") && body.length() > 1) {
			turns = 2;
			body = body.substring(0, body.length() - 1);
		}
		Matcher matcher = TOKEN.matcher(body);
		if (!matcher.matches()) {
			throw new InvalidNotationException("Mouvement inconnu : « " + token + " »");
		}
		String normalized = normalizeSuffix(token);
		if (matcher.group(2) != null) {
			Face face = Face.valueOf(matcher.group(2));
			boolean wide = matcher.group(3) != null;
			int depth = (matcher.group(1) != null) ? Integer.parseInt(matcher.group(1)) : (wide ? 2 : 1);
			if (depth < 1 || depth > size) {
				throw new InvalidNotationException("Tranche hors du cube pour « " + token + " » (taille " + size + ")");
			}
			return faceMove(face, wide ? 1 : depth, depth, turns, size, normalized);
		}
		if (matcher.group(4) != null) {
			if (size < 3) {
				throw new InvalidNotationException("« " + token + " » nécessite un cube 3x3 ou plus");
			}
			Face face = Face.valueOf(matcher.group(4).toUpperCase());
			return faceMove(face, 1, 2, turns, size, normalized);
		}
		if (matcher.group(5) != null) {
			if (size % 2 == 0) {
				throw new InvalidNotationException("« " + token + " » n'existe pas sur un cube pair");
			}
			long middle = 1L << (size / 2);
			return switch (matcher.group(5)) {
				case "M" -> new Move(0, middle, -turns, normalized);
				case "E" -> new Move(1, middle, -turns, normalized);
				default -> new Move(2, middle, turns, normalized);
			};
		}
		long all = (1L << size) - 1;
		int axis = matcher.group(6).charAt(0) - 'x';
		return new Move(axis, all, turns, normalized);
	}

	private static Move faceMove(Face face, int fromDepth, int toDepth, int turns, int size, String notation) {
		int axis = (face.normal(0) != 0) ? 0 : (face.normal(1) != 0) ? 1 : 2;
		int sign = face.normal(axis);
		long mask = 0;
		for (int depth = fromDepth; depth <= toDepth; depth++) {
			int index = (sign > 0) ? size - depth : depth - 1;
			mask |= 1L << index;
		}
		return new Move(axis, mask, sign * turns, notation);
	}

	private static String normalizeSuffix(String token) {
		return token.endsWith("2'") ? token.substring(0, token.length() - 1) : token;
	}

	public Algorithm inverse() {
		List<Move> inverted = new ArrayList<>(this.moves.size());
		for (Move move : this.moves) {
			inverted.add(move.inverse());
		}
		Collections.reverse(inverted);
		return new Algorithm(inverted);
	}

	public Algorithm then(Algorithm other) {
		List<Move> combined = new ArrayList<>(this.moves);
		combined.addAll(other.moves);
		return new Algorithm(combined);
	}

	public int length() {
		return this.moves.size();
	}

	@Override
	public String toString() {
		return String.join(" ", this.moves.stream().map(Move::notation).toList());
	}

}
