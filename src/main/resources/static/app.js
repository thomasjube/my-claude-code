'use strict';

/* ======================================================================= données */

const COLORS = {
	yellow: '#ffd500',
	white: '#ffffff',
	green: '#009b48',
	blue: '#0046ad',
	orange: '#ff5800',
	red: '#b71234',
};

const COLOR_NAMES = {
	yellow: 'jaune', white: 'blanc', green: 'vert', blue: 'bleu', orange: 'orange', red: 'rouge', gray: 'gris',
};

/** Couleur de chaque face d'un cube résolu (jaune en haut, vert devant). */
const HOME = { U: 'yellow', R: 'orange', F: 'green', D: 'white', L: 'red', B: 'blue' };

const SIDE_CYCLE = ['green', 'orange', 'blue', 'red'];

const state = {
	summaries: [],
	puzzles: {},
	group: null,
	trainer: null,
	editor: null,
	sim: null,
};

const app = document.getElementById('app');
const tabs = document.getElementById('tabs');

/* ======================================================================= utilitaires */

function h(tag, attrs = {}, ...children) {
	const el = document.createElement(tag);
	for (const [key, value] of Object.entries(attrs)) {
		if (value === null || value === undefined || value === false) continue;
		if (key.startsWith('on')) el.addEventListener(key.slice(2), value);
		else if (key === 'class') el.className = value;
		else if (key === 'html') el.innerHTML = value;
		else el.setAttribute(key, value === true ? '' : value);
	}
	for (const child of children.flat()) {
		if (child === null || child === undefined || child === false) continue;
		el.append(child instanceof Node ? child : document.createTextNode(child));
	}
	return el;
}

async function api(path, options) {
	const response = await fetch(path, options);
	const body = await response.json().catch(() => ({}));
	if (!response.ok) throw new Error(body.detail || `Erreur ${response.status}`);
	return body;
}

async function loadPuzzle(id) {
	if (!state.puzzles[id]) state.puzzles[id] = await api(`/api/puzzles/${encodeURIComponent(id)}`);
	return state.puzzles[id];
}

function copy(text, button) {
	navigator.clipboard?.writeText(text).then(() => {
		const label = button.textContent;
		button.textContent = 'Copié ✓';
		setTimeout(() => { button.textContent = label; }, 1200);
	});
}

function randomItem(items) {
	return items[Math.floor(Math.random() * items.length)];
}

/* ======================================================================= SVG */

const SVG_NS = 'http://www.w3.org/2000/svg';
let svgCounter = 0;

function s(tag, attrs = {}, ...children) {
	const el = document.createElementNS(SVG_NS, tag);
	for (const [key, value] of Object.entries(attrs)) {
		if (value === null || value === undefined) continue;
		if (key.startsWith('on')) el.addEventListener(key.slice(2), value);
		else el.setAttribute(key, value);
	}
	for (const child of children.flat()) if (child) el.append(child);
	return el;
}

function fill(color) {
	return color === 'gray' ? 'fill: var(--masked)' : `fill: ${COLORS[color] ?? color}`;
}

function sticker(x, y, w, hgt, color, label) {
	return s('rect', {
		x, y, width: w, height: hgt, rx: 0.1, class: 'sticker', style: fill(color),
	}, label ? s('title', {}, label) : null);
}

/**
 * Enveloppe un autocollant pour le rendre cliquable (édition de la dernière couche).
 */
function clickable(node, onClick, label) {
	if (!onClick) return node;
	const group = s('g', {
		class: 'sticker-button', tabindex: 0, role: 'button', 'aria-label': label, onclick: onClick,
		onkeydown: (event) => {
			if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onClick(); }
		},
	}, node);
	return group;
}

/**
 * Vue de dessus de la dernière couche : face U et lignes du haut des faces latérales rabattues.
 * `onEdit(face, index)` rend les cases cliquables.
 */
function topView(diagram, onEdit) {
	const n = diagram.size;
	const strip = 0.32;
	const gap = 0.1;
	const off = strip + gap;
	const total = n + 2 * off;
	const pad = 0.05;
	const faces = diagram.faces;
	const svg = s('svg', {
		viewBox: `${-pad} ${-pad} ${total + 2 * pad} ${total + 2 * pad}`,
		role: 'img',
		'aria-label': 'Vue de dessus de la dernière couche',
	});
	const cell = 0.92;
	const inset = (1 - cell) / 2;
	for (let r = 0; r < n; r++) {
		for (let c = 0; c < n; c++) {
			const color = faces.U[r * n + c];
			const node = sticker(off + c + inset, off + r + inset, cell, cell, color, COLOR_NAMES[color]);
			svg.append(clickable(node, onEdit && (() => onEdit('U', r * n + c)), `Case U ${r + 1}-${c + 1}`));
		}
	}
	const sides = [
		// face, position (x, y, largeur, hauteur) de la case d'indice c
		['F', (c) => [off + c + inset, off + n + gap, cell, strip]],
		['B', (c) => [off + (n - 1 - c) + inset, 0, cell, strip]],
		['R', (c) => [off + n + gap, off + (n - 1 - c) + inset, strip, cell]],
		['L', (c) => [0, off + c + inset, strip, cell]],
	];
	for (const [face, place] of sides) {
		for (let c = 0; c < n; c++) {
			const color = faces[face][c];
			const [x, y, w, hh] = place(c);
			const node = sticker(x, y, w, hh, color, COLOR_NAMES[color]);
			svg.append(clickable(node, onEdit && (() => onEdit(face, c)), `Côté ${face} ${c + 1}`));
		}
	}
	if (diagram.arrows?.length) {
		const id = `ah${++svgCounter}`;
		svg.append(s('defs', {}, s('marker', {
			id, viewBox: '0 0 10 10', refX: 6, refY: 5, markerWidth: 4, markerHeight: 4, orient: 'auto-start-reverse',
		}, s('path', { d: 'M0,0 L10,5 L0,10 z', class: 'arrow-head' }))));
		for (const arrow of diagram.arrows) {
			const [x1, y1] = [off + arrow.from[1] + 0.5, off + arrow.from[0] + 0.5];
			const [x2, y2] = [off + arrow.to[1] + 0.5, off + arrow.to[0] + 0.5];
			const len = Math.hypot(x2 - x1, y2 - y1);
			const k = Math.min(0.28, len / 3) / len;
			svg.append(s('line', {
				x1: x1 + (x2 - x1) * k, y1: y1 + (y2 - y1) * k,
				x2: x2 - (x2 - x1) * k, y2: y2 - (y2 - y1) * k,
				class: 'arrow',
				'marker-end': `url(#${id})`,
				'marker-start': arrow.bothWays ? `url(#${id})` : null,
			}));
		}
	}
	return svg;
}

/** Vue 3D isométrique des faces U, F et R (cas F2L et première couche). */
function isoView(diagram) {
	const n = diagram.size;
	const cos = Math.cos(Math.PI / 6);
	const project = ([x, y, z]) => [(x - z) * cos, (x + z) * 0.5 - y];
	const pad = 0.12;
	const svg = s('svg', {
		viewBox: `${-n * cos - pad} ${-n - pad} ${2 * n * cos + 2 * pad} ${2 * n + 2 * pad}`,
		role: 'img',
		'aria-label': 'Vue 3D des faces U, F et R',
	});
	const outline = [[0, n, 0], [n, n, 0], [n, 0, 0], [n, 0, n], [0, 0, n], [0, n, n]].map(project);
	svg.append(s('polygon', { points: outline.map((p) => p.join(',')).join(' '), class: 'cube-body' }));
	const quad = (corners, color) => {
		const pts = corners.map(project);
		const cx = pts.reduce((a, p) => a + p[0], 0) / 4;
		const cy = pts.reduce((a, p) => a + p[1], 0) / 4;
		const shrunk = pts.map(([x, y]) => [cx + (x - cx) * 0.88, cy + (y - cy) * 0.88]);
		return s('polygon', {
			points: shrunk.map((p) => p.join(',')).join(' '), class: 'sticker', style: fill(color),
		}, s('title', {}, COLOR_NAMES[color]));
	};
	for (let r = 0; r < n; r++) {
		for (let c = 0; c < n; c++) {
			svg.append(quad([[c, n, r], [c + 1, n, r], [c + 1, n, r + 1], [c, n, r + 1]], diagram.faces.U[r * n + c]));
			const top = n - r;
			svg.append(quad([[c, top, n], [c + 1, top, n], [c + 1, top - 1, n], [c, top - 1, n]], diagram.faces.F[r * n + c]));
			svg.append(quad([[n, top, n - c], [n, top, n - c - 1], [n, top - 1, n - c - 1], [n, top - 1, n - c]], diagram.faces.R[r * n + c]));
		}
	}
	return svg;
}

/** Patron complet du cube (simulateur). */
function netView(diagram) {
	const n = diagram.size;
	const gap = 0.2;
	const unit = n + gap;
	const layout = { U: [1, 0], L: [0, 1], F: [1, 1], R: [2, 1], B: [3, 1], D: [1, 2] };
	const svg = s('svg', {
		viewBox: `-0.1 -0.1 ${4 * unit} ${3 * unit}`, role: 'img', 'aria-label': 'Patron du cube',
	});
	for (const [face, [fx, fy]] of Object.entries(layout)) {
		const g = s('g', {}, s('title', {}, `Face ${face}`));
		for (let r = 0; r < n; r++) {
			for (let c = 0; c < n; c++) {
				const color = diagram.faces[face][r * n + c];
				g.append(sticker(fx * unit + c + 0.04, fy * unit + r + 0.04, 0.92, 0.92, color));
			}
		}
		svg.append(g);
	}
	return svg;
}

function diagramView(diagram) {
	if (diagram.type === 'F2L') return isoView(diagram);
	if (diagram.type === 'OLL' || diagram.type === 'PLL') return topView(diagram);
	return netView(diagram);
}

/* ======================================================================= navigation */

function route() {
	const hash = decodeURIComponent(location.hash.replace(/^#\/?/, ''));
	const [path, query = ''] = hash.split('?');
	const [first = '3x3', second] = path.split('/');
	return { first, second, params: new URLSearchParams(query) };
}

function renderTabs(active) {
	tabs.replaceChildren(
		...state.summaries.map((p) => h('a', { href: `#/${p.id}`, 'aria-current': p.id === active ? 'page' : null }, p.name)),
		h('a', { href: '#/simulateur', 'aria-current': active === 'simulateur' ? 'page' : null }, 'Simulateur'),
	);
}

async function render() {
	const { first, second, params } = route();
	renderTabs(first);
	try {
		if (first === 'simulateur') {
			renderSimulator(params);
			return;
		}
		const puzzle = await loadPuzzle(first);
		const stage = puzzle.stages.find((st) => st.id === second)
			?? puzzle.stages.find((st) => st.cases.length) ?? puzzle.stages[0];
		renderPuzzle(puzzle, stage, params.get('mode') || 'liste');
	}
	catch (error) {
		app.replaceChildren(h('p', { class: 'error' }, error.message));
	}
}

window.addEventListener('hashchange', () => {
	state.group = null;
	state.trainer = null;
	state.editor = null;
	render();
});

/* ======================================================================= cube / étape */

function renderPuzzle(puzzle, stage, mode) {
	const modes = [['liste', 'Bibliothèque']];
	if (stage.recognizable) modes.push(['identifier', 'Identifier mon cas']);
	if (stage.cases.length > 1) modes.push(['entrainement', 'Entraînement']);
	if (!modes.some(([id]) => id === mode)) mode = 'liste';

	const content = h('div');
	app.replaceChildren(...[
		h('h1', {}, puzzle.name),
		h('p', { class: 'lead' }, puzzle.summary),
		h('nav', { class: 'stage-nav', 'aria-label': 'Étapes' },
			puzzle.stages.map((st, i) => h('a', {
				class: 'pill', href: `#/${puzzle.id}/${st.id}`, 'aria-current': st.id === stage.id ? 'true' : null,
			}, `${i + 1}. ${st.title}`, st.cases.length ? h('span', { class: 'count' }, String(st.cases.length)) : null))),
		h('section', { class: 'panel' },
			h('h2', {}, stage.title),
			h('p', {}, stage.summary),
			stage.tips.length ? h('ul', { class: 'tips' }, stage.tips.map((tip) => h('li', {}, tip))) : null),
		modes.length > 1 ? h('div', { class: 'toolbar', role: 'tablist' },
			modes.map(([id, label]) => h('a', {
				class: 'pill', role: 'tab', href: `#/${puzzle.id}/${stage.id}${id === 'liste' ? '' : `?mode=${id}`}`,
				'aria-selected': String(id === mode), 'aria-current': id === mode ? 'true' : null,
			}, label))) : null,
		content,
	].filter(Boolean));
	if (mode === 'identifier') renderRecognizer(content, puzzle, stage);
	else if (mode === 'entrainement') renderTrainer(content, puzzle, stage);
	else renderLibrary(content, puzzle, stage);
}

function groupsOf(stage) {
	return [...new Set(stage.cases.map((c) => c.group))];
}

function groupChips(stage, onChange) {
	const groups = groupsOf(stage);
	if (groups.length < 2) return null;
	const chip = (label, value) => h('button', {
		class: 'pill', type: 'button', 'aria-pressed': String(state.group === value),
		onclick: () => { state.group = value; onChange(); },
	}, label, h('span', { class: 'count' }, String(value ? stage.cases.filter((c) => c.group === value).length : stage.cases.length)));
	return h('div', { class: 'chips', role: 'group', 'aria-label': 'Filtrer par famille' },
		chip('Tous', null), groups.map((g) => chip(g, g)));
}

function caseCard(puzzle, algCase) {
	const copyButton = h('button', { class: 'btn small', type: 'button' }, 'Copier');
	copyButton.addEventListener('click', () => copy(algCase.algorithm, copyButton));
	const simulate = `#/simulateur?size=${puzzle.size}&setup=${encodeURIComponent(algCase.setup)}&alg=${encodeURIComponent(algCase.algorithm)}`;
	return h('article', { class: 'card' },
		h('div', { class: 'card-head' },
			h('span', { class: 'card-title' }, algCase.name),
			algCase.group ? h('span', { class: 'badge' }, algCase.group) : null),
		h('div', { class: 'diagram' }, diagramView(algCase.diagram)),
		h('div', { class: 'alg' }, algCase.algorithm),
		h('details', { class: 'setup' },
			h('summary', {}, 'Reproduire ce cas'),
			h('p', {}, 'Depuis un cube résolu (jaune en haut, vert devant) : '),
			h('code', {}, algCase.setup)),
		h('div', { class: 'card-foot' },
			h('span', { class: 'muted', title: 'Nombre de mouvements (rotations du cube exclues)' }, `${algCase.moveCount} coups`),
			h('span', { class: 'spacer' }),
			copyButton,
			h('a', { class: 'btn small', href: simulate }, 'Simuler')));
}

function renderLibrary(container, puzzle, stage) {
	if (!stage.cases.length) {
		container.replaceChildren();
		return;
	}
	const draw = () => {
		const cases = stage.cases.filter((c) => !state.group || c.group === state.group);
		container.replaceChildren(
			groupChips(stage, draw) ?? '',
			h('div', { class: 'grid' }, cases.map((c) => caseCard(puzzle, c))));
	};
	draw();
}

/* ======================================================================= entraînement */

function renderTrainer(container, puzzle, stage) {
	const draw = () => {
		const pool = stage.cases.filter((c) => !state.group || c.group === state.group);
		if (!state.trainer || !pool.includes(state.trainer.current)) {
			state.trainer = { current: randomItem(pool), revealed: false, seen: state.trainer?.seen ?? 0 };
		}
		const t = state.trainer;
		const next = () => {
			const others = pool.length > 1 ? pool.filter((c) => c !== t.current) : pool;
			state.trainer = { current: randomItem(others), revealed: false, seen: t.seen + 1 };
			draw();
		};
		const alg = h('div', { class: `alg${t.revealed ? '' : ' hidden-alg'}`, 'aria-hidden': t.revealed ? null : 'true' },
			t.current.algorithm);
		container.replaceChildren(
			groupChips(stage, draw) ?? '',
			h('section', { class: 'panel trainer' },
				h('p', { class: 'muted' }, 'Reconnaissez le cas et retrouvez son algorithme, puis vérifiez.'),
				h('div', { class: 'diagram' }, diagramView(t.current.diagram)),
				t.revealed ? h('strong', {}, t.current.name) : h('strong', {}, '?'),
				alg,
				h('div', { class: 'toolbar' },
					t.revealed ? null : h('button', {
						class: 'btn', type: 'button', onclick: () => { t.revealed = true; draw(); },
					}, 'Voir la solution'),
					h('button', { class: 'btn primary', type: 'button', onclick: next }, 'Cas suivant')),
				h('p', { class: 'muted' }, `${t.seen} cas travaillé${t.seen > 1 ? 's' : ''} · ${pool.length} dans la sélection`)));
	};
	draw();
}

/* ======================================================================= identification */

function emptyEditor(puzzle, stage) {
	const n = puzzle.size;
	const oll = stage.diagramType === 'OLL';
	const faces = { U: Array(n * n).fill('yellow') };
	for (const [face, color] of [['F', 'green'], ['R', 'orange'], ['B', 'blue'], ['L', 'red']]) {
		faces[face] = Array(n).fill(oll ? 'gray' : color);
	}
	return { key: `${puzzle.id}/${stage.id}`, faces, result: null };
}

function renderRecognizer(container, puzzle, stage) {
	const n = puzzle.size;
	const oll = stage.diagramType === 'OLL';
	if (!state.editor || state.editor.key !== `${puzzle.id}/${stage.id}`) state.editor = emptyEditor(puzzle, stage);
	const editor = state.editor;
	const centerIndex = n % 2 === 1 ? Math.floor(n * n / 2) : -1;

	const onEdit = (face, index) => {
		const cells = editor.faces[face];
		if (oll) {
			if (face === 'U' && index === centerIndex) return;
			cells[index] = cells[index] === 'yellow' ? 'gray' : 'yellow';
		}
		else {
			if (face === 'U') return;
			cells[index] = SIDE_CYCLE[(SIDE_CYCLE.indexOf(cells[index]) + 1) % SIDE_CYCLE.length];
		}
		editor.result = null;
		draw();
	};

	const submit = async () => {
		try {
			editor.result = await api(`/api/puzzles/${puzzle.id}/stages/${stage.id}/recognize`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					top: editor.faces.U, front: editor.faces.F, right: editor.faces.R, back: editor.faces.B, left: editor.faces.L,
				}),
			});
		}
		catch (error) {
			editor.result = { found: false, message: error.message };
		}
		draw();
	};

	const resultView = () => {
		const r = editor.result;
		if (!r) return h('p', { class: 'muted' }, 'Le résultat s’affichera ici.');
		const matched = r.caseId && stage.cases.find((c) => c.id === r.caseId);
		return h('div', {},
			h('div', { class: `result ${r.found ? 'ok' : 'ko'}` },
				h('div', {}, r.message),
				r.solution ? h('div', { class: 'alg' }, r.solution) : null,
				r.caseId && (r.preAuf || r.postAuf) ? h('p', { class: 'muted' },
					[r.preAuf && `Avant : ${r.preAuf}`, `Algorithme : ${r.algorithm}`, r.postAuf && `Après : ${r.postAuf}`]
						.filter(Boolean).join(' · ')) : null),
			matched ? h('div', { class: 'grid', style: 'margin-top:12px' }, caseCard(puzzle, matched)) : null);
	};

	const draw = () => {
		const diagram = { size: n, faces: editor.faces, arrows: [] };
		container.replaceChildren(h('section', { class: 'panel' },
			h('div', { class: 'split' },
				h('div', { class: 'editor' },
					topView(diagram, onEdit),
					h('div', { class: 'toolbar', style: 'margin-top:8px' },
						h('button', { class: 'btn primary', type: 'button', onclick: submit }, 'Identifier'),
						h('button', {
							class: 'btn', type: 'button',
							onclick: () => { state.editor = emptyEditor(puzzle, stage); renderRecognizer(container, puzzle, stage); },
						}, 'Réinitialiser'))),
				h('div', {},
					h('p', {}, oll
						? 'Tenez le cube jaune en haut. Cliquez sur les cases pour indiquer où se trouvent les autocollants jaunes : sur le dessus et sur les côtés (bandes autour), vus depuis le haut.'
						: 'Tenez le cube jaune en haut et vert devant. Cliquez sur les bandes latérales pour reproduire les couleurs de la couche du haut (chaque clic passe à la couleur suivante).'),
					h('p', { class: 'muted' }, 'La bande du bas correspond à la face avant, celle de droite à la face droite, etc.'),
					resultView()))));
	};
	draw();
}

/* ======================================================================= simulateur */

const SCRAMBLE = {
	2: { faces: ['R', 'U', 'F'], wide: [], length: 11 },
	3: { faces: ['R', 'L', 'U', 'D', 'F', 'B'], wide: [], length: 20 },
	4: { faces: ['R', 'L', 'U', 'D', 'F', 'B'], wide: ['Rw', 'Uw', 'Fw'], length: 40 },
};

const AXIS = { R: 'x', L: 'x', U: 'y', D: 'y', F: 'z', B: 'z' };

function scramble(size) {
	const conf = SCRAMBLE[size];
	const moves = [];
	let lastAxis = null;
	let sameAxisCount = 0;
	while (moves.length < conf.length) {
		const base = randomItem([...conf.faces, ...conf.wide]);
		const axis = AXIS[base[0]];
		if (axis === lastAxis && (sameAxisCount >= 1 || moves[moves.length - 1][0] === base[0])) continue;
		sameAxisCount = axis === lastAxis ? sameAxisCount + 1 : 0;
		lastAxis = axis;
		moves.push(base + randomItem(['', "'", '2']));
	}
	return moves.join(' ');
}

function isSolved(diagram) {
	return Object.entries(diagram.faces).every(([face, cells]) => cells.every((c) => c === HOME[face]));
}

function renderSimulator(params) {
	const size = Number(params.get('size')) || state.sim?.size || 3;
	const setup = params.get('setup') || '';
	const alg = params.get('alg') || '';
	if (!state.sim || params.has('setup')) {
		state.sim = { size, text: [setup, alg].filter(Boolean).join(' '), start: null, data: null, step: 0, error: null, timer: null };
		if (setup) state.sim.start = setup.trim().split(/\s+/).length;
	}
	const sim = state.sim;

	const sizeSelect = h('select', { id: 'sim-size' },
		[2, 3, 4].map((n) => h('option', { value: n, selected: n === sim.size }, `${n}x${n}`)));
	const textarea = h('textarea', { id: 'sim-moves', spellcheck: 'false', placeholder: "Ex. : R U R' U' R' F R2 U' R' U' R U R' F'" }, sim.text);

	const stop = () => { clearInterval(sim.timer); sim.timer = null; };

	const load = async (startStep) => {
		stop();
		sim.size = Number(sizeSelect.value);
		sim.text = textarea.value;
		try {
			sim.data = await api(`/api/simulate?size=${sim.size}&moves=${encodeURIComponent(sim.text)}`);
			sim.error = null;
			sim.step = Math.min(startStep ?? sim.data.moves.length, sim.data.moves.length);
		}
		catch (error) {
			sim.error = error.message;
		}
		draw();
	};

	const go = (step) => {
		if (!sim.data) return;
		sim.step = Math.max(0, Math.min(step, sim.data.moves.length));
		draw();
	};

	const play = () => {
		if (sim.timer) { stop(); draw(); return; }
		if (sim.step >= sim.data.moves.length) sim.step = sim.start ?? 0;
		sim.timer = setInterval(() => {
			if (sim.step >= sim.data.moves.length) { stop(); draw(); return; }
			go(sim.step + 1);
		}, 550);
		draw();
	};

	const view = h('div');
	const draw = () => {
		if (!sim.data) { view.replaceChildren(sim.error ? h('p', { class: 'error' }, sim.error) : ''); return; }
		const frame = sim.data.frames[sim.step];
		const solved = isSolved(frame);
		const total = sim.data.moves.length;
		view.replaceChildren(
			sim.error ? h('p', { class: 'error' }, sim.error) : '',
			h('div', { class: 'toolbar' },
				h('button', { class: 'btn', type: 'button', onclick: () => go(0), 'aria-label': 'Début' }, '⏮'),
				h('button', { class: 'btn', type: 'button', onclick: () => go(sim.step - 1), 'aria-label': 'Mouvement précédent' }, '◀'),
				h('button', { class: 'btn primary', type: 'button', onclick: play }, sim.timer ? 'Pause' : 'Lecture'),
				h('button', { class: 'btn', type: 'button', onclick: () => go(sim.step + 1), 'aria-label': 'Mouvement suivant' }, '▶'),
				h('button', { class: 'btn', type: 'button', onclick: () => go(total), 'aria-label': 'Fin' }, '⏭'),
				h('span', { class: 'muted' }, `${sim.step} / ${total}`),
				h('span', { class: 'spacer' }),
				h('span', { class: `status${solved ? ' solved' : ''}` }, solved ? 'Cube résolu ✓' : 'Non résolu')),
			h('div', { class: 'moves', 'aria-label': 'Mouvements' }, sim.data.moves.map((m, i) => h('span', {
				class: i < sim.step - 1 ? 'done' : i === sim.step - 1 ? 'current' : '',
				title: sim.start !== null && i < sim.start ? 'Mise en place du cas' : null,
			}, m))),
			h('div', { class: 'net', style: 'margin-top:12px' }, netView(frame)));
	};

	app.replaceChildren(
		h('h1', {}, 'Simulateur'),
		h('p', { class: 'lead' }, 'Saisissez une séquence de mouvements (ou un mélange), puis rejouez-la pas à pas sur le patron du cube.'),
		h('section', { class: 'panel' },
			h('div', { class: 'sim-controls' },
				h('label', { for: 'sim-size' }, 'Cube'), sizeSelect,
				h('label', { for: 'sim-moves' }, 'Mouvements'), textarea,
				h('div', { class: 'toolbar' },
					h('button', { class: 'btn primary', type: 'button', onclick: () => load() }, 'Appliquer'),
					h('button', {
						class: 'btn', type: 'button',
						onclick: () => { textarea.value = scramble(Number(sizeSelect.value)); sim.start = null; load(); },
					}, 'Mélanger'),
					h('button', {
						class: 'btn', type: 'button',
						onclick: () => { textarea.value = ''; sim.start = null; load(0); },
					}, 'Réinitialiser'))),
			sim.start !== null ? h('p', { class: 'muted', style: 'margin-top:8px' },
				`Les ${sim.start} premiers mouvements mettent le cas en place ; la suite est l'algorithme. Utilisez ▶ pour le suivre.`) : null),
		view);
	load(sim.start ?? undefined);
}

/* ======================================================================= démarrage */

(async () => {
	try {
		state.summaries = await api('/api/puzzles');
		if (!location.hash) history.replaceState(null, '', '#/3x3');
		await render();
	}
	catch (error) {
		app.replaceChildren(h('p', { class: 'error' }, `Impossible de charger les données : ${error.message}`));
	}
})();
