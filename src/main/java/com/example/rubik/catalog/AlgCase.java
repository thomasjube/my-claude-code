package com.example.rubik.catalog;

/**
 * Un cas et l'algorithme qui le résout.
 *
 * @param id identifiant unique dans l'étape (ex. {@code oll-27})
 * @param name nom affiché
 * @param group famille du cas (forme, type de permutation...)
 * @param algorithm algorithme en notation standard
 */
public record AlgCase(String id, String name, String group, String algorithm) {
}
