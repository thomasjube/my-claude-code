# Rubik's Helper

Application web d'aide à la résolution des Rubik's cubes **2x2, 3x3 et 4x4**, basée sur
**Spring Boot 4.1.1** et **Java 21**.

## Fonctionnalités

| Cube | Étapes |
|------|--------|
| 2x2 | Première couche (5 cas), OLL (7 cas), PLL (2 cas) |
| 3x3 | Croix, **F2L (41 cas)**, **OLL (57 cas)**, **PLL (21 cas)** — méthode CFOP |
| 4x4 | Centres, appariement des arêtes, résolution 3x3, **parités OLL et PLL** |

- **Bibliothèque** : chaque cas avec son diagramme, son algorithme, le nombre de coups et la
  séquence pour le reproduire sur un cube résolu ; filtre par famille (forme d'OLL, type de PLL…).
- **Identifier mon cas** (OLL / PLL) : reproduisez la dernière couche de votre cube en cliquant sur
  les cases ; l'application trouve le cas, l'ajustement de U (AUF) à faire avant et après, et
  l'algorithme complet.
- **Entraînement** : cas tirés au hasard, solution masquée.
- **Simulateur** : applique une séquence (ou un mélange aléatoire) et la rejoue pas à pas sur le
  patron du cube.

Orientation de référence : **jaune en haut, vert devant**.

## Fiabilité des algorithmes

Un moteur de cube NxN (`com.example.rubik.cube`) exécute la notation complète (R U F L D B, `'`,
`2`, Rw / r, 2R, M E S, x y z). Les diagrammes sont **calculés à partir des algorithmes** (état =
inverse de l'algorithme appliqué à un cube résolu), ils sont donc toujours cohérents avec eux.

Les tests vérifient chaque algorithme sur ce moteur :

- il ne touche qu'à ce que son étape autorise (F2L : l'emplacement avant-droit et la couche U ;
  OLL / PLL : la couche U ; PLL : la face jaune reste orientée) ;
- tous les cas d'une étape sont distincts (à un AUF près), donc la couverture est complète
  (41 F2L, 57 OLL, 21 PLL) ;
- la reconnaissance retrouve chaque cas quel que soit l'AUF, et la solution proposée résout le cube.

## Lancer

```bash
./mvnw spring-boot:run      # puis http://localhost:8080
./mvnw verify               # tests + jar exécutable
```

## API

| Méthode | Chemin | Description |
|---------|--------|-------------|
| GET | `/api/puzzles` | Liste des cubes et de leurs étapes |
| GET | `/api/puzzles/{id}` | Étapes, cas, algorithmes et diagrammes (`2x2`, `3x3`, `4x4`) |
| POST | `/api/puzzles/{id}/stages/{stage}/recognize` | Identifie un cas OLL / PLL à partir de la dernière couche |
| GET | `/api/simulate?size=3&moves=R U R' U'` | États successifs du cube pour une séquence |

Exemple de reconnaissance (Sune) :

```bash
curl -X POST localhost:8080/api/puzzles/3x3/stages/oll/recognize \
  -H 'Content-Type: application/json' \
  -d '{"top":["gray","yellow","gray","yellow","yellow","yellow","yellow","yellow","gray"],
       "front":["gray","gray","yellow"],"right":["gray","gray","yellow"],
       "back":["gray","gray","yellow"],"left":["gray","gray","gray"]}'
```
