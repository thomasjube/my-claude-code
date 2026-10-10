// Solveur « IA responsables » : glouton à prix + recherche à voisinage large (LNS).
//
// Usage : solver <instance.txt> <sortie.json> [options clé=valeur]
//   time=secondes seed=n wE= wD= wF= wV= alias=0/1 sources=0/1 init=<solution.txt>
//
// Modèle :
//   - un modèle entraîné (« item ») remplit chacun de ses besoins soit avec des datasets,
//     soit avec un modèle source (modèle à besoin unique, rempli lui-même par des datasets) ;
//   - valeur pleine si tous ses datasets sont libres et sans source, sinon moitié ;
//   - option alias : copie supplémentaire d'un modèle sous l'identifiant (i - N), dont tous
//     les besoins sont remplis par des sources (le correcteur ne borne pas ces identifiants).
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

static int NM, ND, MAXS = 1;
static ll CAP;
struct Req { int t, L, U; };
static vector<int> val;
static vector<ll> En;
static vector<vector<Req>> reqs;
static vector<int> dsT, dsS, dsC;

// ------------------------------------------------------------------ paramètres
static double P_time = 60, P_wE = 1, P_wD = 0, P_wF = 0, P_wV = 0.5, P_theta = 1.0;
static int P_alias = 0, P_sources = 1, P_seed = 1, P_pairLim = 400, P_srcTries = 30;
static double P_kmin = 2, P_kmax = 20, P_T0 = -1, P_noise = 0.15;
static string P_init, P_out, P_plan;
static double P_planBoost = 20;
static int P_aliasFirst = 0;
static int P_halfCop = 0;
static int P_tinyU = 1000;
static int P_hugeL = 50000;  // modèles « moitié » : datasets non libres d'abord exclusivement  // alias placés avant les modèles pleins
static int P_planOrder = 0;  // 0 : gros besoins d'abord ; 1 : petites fenêtres ; 2 : fenêtres étroites ; 3 : aléatoire
// plan (solution MILP) : rôle prévu et besoins à sourcer
static vector<char> planFull, planHalf, planSrc, planAlias;
static vector<vector<char>> planZ;

static mt19937_64 rng;
static inline double urand() { return (rng() >> 11) * (1.0 / 9007199254740992.0); }
static inline int irand(int n) { return (int)(rng() % (unsigned long long)n); }

// ------------------------------------------------------------------ pools de datasets
static vector<char> avail;
struct Pool {
    ll units = 0;  // volume total disponible
    vector<vector<int>> bk;
    vector<int> cnt;
    vector<uint64_t> bits;
    void init() {
        bk.assign(MAXS + 1, {});
        cnt.assign(MAXS + 1, 0);
        bits.assign(MAXS / 64 + 2, 0);
    }
    inline void inc(int s) { units += s; if (cnt[s]++ == 0) bits[s >> 6] |= 1ULL << (s & 63); }
    inline void dec(int s) { units -= s; if (--cnt[s] == 0) bits[s >> 6] &= ~(1ULL << (s & 63)); }
    int findLE(int x) const {
        if (x < 1) return -1;
        if (x > MAXS) x = MAXS;
        int w = x >> 6, b = x & 63;
        uint64_t m = bits[w] & (b == 63 ? ~0ULL : ((1ULL << (b + 1)) - 1));
        while (true) {
            if (m) return w * 64 + 63 - __builtin_clzll(m);
            if (--w < 0) return -1;
            m = bits[w];
        }
    }
    int findGE(int lo, int hi) const {
        if (lo < 1) lo = 1;
        if (hi > MAXS) hi = MAXS;
        if (lo > hi) return -1;
        int w = lo >> 6;
        uint64_t m = bits[w] & (~0ULL << (lo & 63));
        int wmax = hi >> 6;
        while (true) {
            if (m) {
                int s = w * 64 + __builtin_ctzll(m);
                return s <= hi ? s : -1;
            }
            if (++w > wmax) return -1;
            m = bits[w];
        }
    }
};
static Pool pools[8];  // indice = type * 2 + copyright
static vector<int> stampv;
static int stampc = 0;

static inline void dsAdd(int id) {
    avail[id] = 1;
    Pool &p = pools[dsT[id] * 2 + dsC[id]];
    int s = dsS[id];
    p.inc(s);
    auto &b = p.bk[s];
    b.push_back(id);
    if ((int)b.size() > 4 * p.cnt[s] + 16) {  // compactage des entrées périmées
        ++stampc;
        vector<int> nb;
        for (int x : b)
            if (avail[x] && stampv[x] != stampc) { stampv[x] = stampc; nb.push_back(x); }
        b.swap(nb);
    }
}
static inline void dsTake(int id) {
    avail[id] = 0;
    pools[dsT[id] * 2 + dsC[id]].dec(dsS[id]);
}
static inline int popSize(Pool &p, int s) {
    auto &b = p.bk[s];
    while (true) {
        int id = b.back();
        b.pop_back();
        if (avail[id]) { dsTake(id); return id; }
    }
}

// mode 0 : datasets libres uniquement ; mode 1 : non libres de préférence, puis libres
static inline int pickGE(int t, int mode, int lo, int hi, int &pool) {
    if (mode == 0) { pool = t * 2; return pools[pool].findGE(lo, hi); }
    if (mode == 2) { pool = t * 2 + 1; return pools[pool].findGE(lo, hi); }
    int c = pools[t * 2 + 1].findGE(lo, hi);
    if (c >= 0) { pool = t * 2 + 1; return c; }
    pool = t * 2;
    return pools[pool].findGE(lo, hi);
}
static inline int pickLE(int t, int mode, int x, int &pool) {
    if (mode == 0) { pool = t * 2; return pools[pool].findLE(x); }
    if (mode == 2) { pool = t * 2 + 1; return pools[pool].findLE(x); }
    int c = pools[t * 2 + 1].findLE(x), f = pools[t * 2].findLE(x);
    if (c >= 0 && (f < 0 || c * 10 >= f * 8)) { pool = t * 2 + 1; return c; }
    pool = t * 2;
    return f;
}

// Remplit un besoin [L, U] de type t. Ajoute les datasets pris à picks. Annule en cas d'échec.
static bool fillReq(int t, int L, int U, int mode, vector<int> &picks) {
    if (U < L) return false;
    ll availUnits = (mode == 2 ? 0 : pools[t * 2].units) + (mode >= 1 ? pools[t * 2 + 1].units : 0);
    if (availUnits < L) return false;
    size_t start = picks.size();
    int got = 0;
    while (true) {
        int R = L - got, room = U - got;
        if (R <= 0) return true;
        int pool, s = pickGE(t, mode, R, room, pool);
        bool done = false;
        // finisseur au dépassement minimal : un dataset seul ou une paire (a, b)
        int bestOver = (s >= 0) ? s - R : INT_MAX, ba = -1, bpa = -1, bb = -1, bpb = -1;
        if (bestOver > 0 && R <= 2 * MAXS) {
            int a = min(room - 1, MAXS), tries = 0;
            while (tries++ < P_pairLim) {
                int pa;
                a = pickLE(t, mode, a, pa);
                if (a < 1 || 2 * a < R) break;
                int lo = R - a, hi = min(room - a, a);
                int pb = -1, b = -1;
                if (lo <= hi) {
                    b = pickGE(t, mode, lo, hi, pb);
                    if (b == a && pb == pa && pools[pa].cnt[a] < 2) {
                        int b2 = pickGE(t, mode, lo, a - 1, pb);
                        if (b2 < 0 && mode == 1) {
                            int other = (pa == t * 2) ? t * 2 + 1 : t * 2;
                            if (pools[other].findGE(a, a) == a) { b2 = a; pb = other; }
                        }
                        b = b2;
                    }
                }
                if (b >= 1 && a + b - R < bestOver) {
                    bestOver = a + b - R; ba = a; bpa = pa; bb = b; bpb = pb;
                    if (bestOver == 0) break;
                }
                a--;
            }
        }
        if (ba >= 0) {
            picks.push_back(popSize(pools[bpa], ba));
            picks.push_back(popSize(pools[bpb], bb));
            return true;
        }
        if (s >= 0) { picks.push_back(popSize(pools[pool], s)); return true; }
        if (!done) {
            int lim = (R > MAXS) ? min(room, MAXS) : R - 1;
            s = pickLE(t, mode, lim, pool);
            if (s < 1) {
                for (size_t i = start; i < picks.size(); i++) dsAdd(picks[i]);
                picks.resize(start);
                return false;
            }
            picks.push_back(popSize(pools[pool], s));
            got += s;
        }
    }
}

// ------------------------------------------------------------------ état
enum { NONE = 0, TRAINED = 1, SOURCE = 2 };
static vector<char> role, aliasOn;
static vector<vector<int>> srcList;  // singles par type, triés par coût
static vector<double> srcKey;
static vector<int> single;  // type si modèle à besoin unique, -1 sinon
static vector<int> srcPos;  // position dans srcList[type]
static int srcPtr[4];       // avant srcPtr[t], toutes les sources de type t sont prises
static inline void srcFreed(int s) { if (single[s] >= 0 && srcPos[s] >= 0) srcPtr[single[s]] = min(srcPtr[single[s]], srcPos[s]); }
static double supplyT[4], freeT[4], totalV;

struct Src { int s; int ridx; vector<int> data; };
struct Item {
    int m; bool alias; int value; ll energy;
    vector<int> data;
    vector<Src> src;
};
static vector<Item> items;           // emplacements (libres si m < 0)
static vector<int> freeSlots;
static vector<int> itemOfModel, itemOfAlias;
static ll energyUsed = 0;
static ll curValue = 0;

static int addItem(Item &&it) {
    int idx;
    if (!freeSlots.empty()) { idx = freeSlots.back(); freeSlots.pop_back(); items[idx] = std::move(it); }
    else { idx = items.size(); items.push_back(std::move(it)); }
    Item &x = items[idx];
    if (x.alias) { aliasOn[x.m] = 1; itemOfAlias[x.m] = idx; }
    else { role[x.m] = TRAINED; itemOfModel[x.m] = idx; }
    for (auto &s : x.src) role[s.s] = SOURCE;
    energyUsed += x.energy;
    curValue += x.value;
    return idx;
}
static Item removeItem(int idx) {
    Item x = std::move(items[idx]);
    items[idx].m = -1;
    freeSlots.push_back(idx);
    if (x.alias) { aliasOn[x.m] = 0; itemOfAlias[x.m] = -1; }
    else { role[x.m] = NONE; itemOfModel[x.m] = -1; }
    for (int d : x.data) dsAdd(d);
    for (auto &s : x.src) { role[s.s] = NONE; srcFreed(s.s); for (int d : s.data) dsAdd(d); }
    if (!x.alias) srcFreed(x.m);
    energyUsed -= x.energy;
    curValue -= x.value;
    return x;
}
// réinsère un item exact (ses datasets doivent être disponibles)
static void restoreItem(const Item &x) {
    for (int d : x.data) dsTake(d);
    for (auto &s : x.src) for (int d : s.data) dsTake(d);
    Item c = x;
    addItem(std::move(c));
}

// trouve une source de type t (hors exclusions), la remplit ; renvoie true si succès
static bool findSource(int t, int exclude, ll energyLeft, Src &out) {
    int tries = 0;
    auto &lst = srcList[t];
    while (srcPtr[t] < (int)lst.size() && role[lst[srcPtr[t]]] != NONE) srcPtr[t]++;
    for (int i = srcPtr[t]; i < (int)lst.size(); i++) {
        int s = lst[i];
        if (role[s] != NONE || s == exclude) continue;
        if (En[s] > energyLeft) continue;
        if (tries++ >= P_srcTries) break;
        const Req &r = reqs[s][0];
        out.data.clear();
        if (fillReq(t, r.L, r.U, 1, out.data)) { out.s = s; role[s] = SOURCE; return true; }
    }
    return false;
}

static double dataCost(int t, int L) { return P_wD * L / supplyT[t]; }
static double srcCostEst[4];

// Tente d'entraîner le modèle m (ou son alias). Mode : 0 = auto, 1 = plein seulement, 2 = moitié seulement.
static bool tryInsert(int m, bool alias, int mode = 0) {
    if (alias ? aliasOn[m] : role[m] != NONE) return false;
    ll left = CAP - energyUsed - En[m];
    if (left < 0) return false;
    const auto &rq = reqs[m];
    // plein : tous les besoins avec des datasets libres
    if (!alias && mode != 2) {
        bool wantFull = true;
        if (mode == 0 && P_theta > 1.0) {
            // option : refuser le plein si la moitié est bien moins coûteuse en données libres
        }
        if (wantFull) {
            Item it; it.m = m; it.alias = false; it.value = val[m]; it.energy = En[m];
            bool ok = true;
            for (auto &r : rq) if (!fillReq(r.t, r.L, r.U, 0, it.data)) { ok = false; break; }
            if (ok) { addItem(std::move(it)); return true; }
            for (int d : it.data) dsAdd(d);
        }
        if (mode == 1) return false;
    }
    if (val[m] / 2 <= 0 && val[m] <= 0) return false;
    // moitié : données (non libres d'abord) ou sources
    Item it; it.m = m; it.alias = alias; it.value = val[m] / 2; it.energy = En[m];
    if (it.value <= 0) return false;
    bool ok = true;
    for (int i = 0; i < (int)rq.size() && ok; i++) {
        const Req &r = rq[i];
        bool feasibleData = !alias && r.U >= r.L;
        bool preferSrc = alias || !feasibleData ||
                         (P_sources && srcCostEst[r.t] < dataCost(r.t, r.L));
        if (!alias && feasibleData && !planZ.empty() && (planHalf[m] || planFull[m])) preferSrc = planZ[m][i];
        bool done = false;
        for (int attempt = 0; attempt < 2 && !done; attempt++) {
            bool useSrc = (attempt == 0) ? preferSrc : !preferSrc;
            if (useSrc) {
                if (!P_sources && !alias) continue;
                Src s;
                if (findSource(r.t, m, left - (it.energy - En[m]), s)) {
                    s.ridx = i;
                    it.energy += En[s.s];
                    it.src.push_back(std::move(s));
                    done = true;
                }
            } else if (feasibleData) {
                if (P_halfCop && fillReq(r.t, r.L, r.U, 2, it.data)) done = true;
                else if (fillReq(r.t, r.L, r.U, 1, it.data)) done = true;
            }
        }
        if (!done) ok = false;
    }
    if (ok && energyUsed + it.energy <= CAP) {
        // si aucun dataset non libre ni source : valeur pleine
        if (!alias && it.src.empty()) {
            bool anyCop = false;
            for (int d : it.data) anyCop |= dsC[d];
            if (!anyCop) it.value = val[m];
        }
        addItem(std::move(it));
        return true;
    }
    for (int d : it.data) dsAdd(d);
    for (auto &s : it.src) { role[s.s] = NONE; srcFreed(s.s); for (int d : s.data) dsAdd(d); }
    return false;
}

// ------------------------------------------------------------------ priorités
struct Cand { int m; bool alias; double prio; };
static vector<Cand> cands;

static void computePriorities() {
    // coût estimé d'une source par type : moyenne des 20 % moins chères
    for (int t = 0; t < 4; t++) {
        auto &l = srcList[t];
        int k = max(1, (int)l.size() / 5);
        double s = 0; int n = 0;
        for (int i = 0; i < (int)l.size() && n < k; i++, n++) s += srcKey[l[i]];
        srcCostEst[t] = n ? s / n : 1e18;
    }
    cands.clear();
    for (int m = 0; m < NM; m++) {
        double e = P_wE * (double)En[m] / CAP + 1e-12;
        double full = e, half = e, srcOnly = e;
        bool fullOk = true, halfOk = true;
        for (auto &r : reqs[m]) {
            bool feas = r.U >= r.L;
            double dc = dataCost(r.t, r.L);
            if (!feas) fullOk = false;
            full += dc + P_wF * r.L / max(1.0, freeT[r.t]);
            double sc = P_sources ? srcCostEst[r.t] : 1e18;
            double hc = feas ? min(dc, sc) : sc;
            if (hc >= 1e17) halfOk = false;
            half += hc;
            srcOnly += srcCostEst[r.t];
        }
        double best = 0;
        if (fullOk) best = max(best, val[m] / full);
        if (halfOk) best = max(best, (val[m] / 2) / half);
        double boost = (!planFull.empty() && (planFull[m] || planHalf[m])) ? P_planBoost : 1.0;
        double aboost = (!planAlias.empty() && planAlias[m]) ? P_planBoost : 1.0;
        if (!planSrc.empty() && planSrc[m]) boost = 1.0 / P_planBoost;  // à garder comme source
        if (best > 0) cands.push_back({m, false, best * boost});
        if (P_alias && val[m] / 2 > 0 && srcOnly < 1e17) cands.push_back({m, true, (val[m] / 2) / srcOnly * aboost});
    }
}

// ------------------------------------------------------------------ sortie
static void writeSolution(const string &path, const vector<Item> &items) {
    string tmp = path + ".tmp";
    FILE *f = fopen(tmp.c_str(), "w");
    fprintf(f, "{\"dataMappings\":[");
    bool first = true;
    for (auto &x : items) {
        if (x.m < 0) continue;
        for (int d : x.data) { fprintf(f, "%s[%d,%d]", first ? "" : ",", d, x.m); first = false; }
        for (auto &s : x.src)
            for (int d : s.data) { fprintf(f, "%s[%d,%d]", first ? "" : ",", d, s.s); first = false; }
    }
    fprintf(f, "],\"modelMappings\":[");
    first = true;
    for (auto &x : items) {
        if (x.m < 0) continue;
        int target = x.alias ? x.m - NM : x.m;
        for (auto &s : x.src) { fprintf(f, "%s[%d,%d]", first ? "" : ",", s.s, target); first = false; }
    }
    fprintf(f, "]}\n");
    fclose(f);
    rename(tmp.c_str(), path.c_str());
}

// Chargement d'une solution au format texte : lignes « D ds modele » et « M source cible »
static void loadSolution(const string &path) {
    ifstream in(path);
    if (!in) { fprintf(stderr, "init introuvable : %s\n", path.c_str()); return; }
    map<int, vector<int>> dataOf;           // modèle -> datasets
    vector<pair<int, int>> mm;
    char c; int a, b;
    while (in >> c >> a >> b) {
        if (c == 'D') dataOf[b].push_back(a);
        else mm.push_back({a, b});
    }
    set<int> sources;
    map<int, vector<int>> srcOf;  // cible (id brut) -> sources
    for (auto &p : mm) { sources.insert(p.first); srcOf[p.second].push_back(p.first); }
    set<int> targets;
    for (auto &p : dataOf) if (!sources.count(p.first)) targets.insert(p.first);
    for (auto &p : srcOf) targets.insert(p.first);
    for (int raw : targets) {
        bool alias = raw < 0;
        int m = alias ? raw + NM : raw;
        Item it; it.m = m; it.alias = alias; it.energy = En[m];
        bool pen = alias;
        if (!alias) for (int d : dataOf[raw]) { it.data.push_back(d); pen |= dsC[d]; }
        for (int s : srcOf[raw]) {
            Src x; x.s = s; x.ridx = -1; x.data = dataOf[s];
            for (int i = 0; i < (int)reqs[m].size(); i++) if (reqs[m][i].t == single[s]) x.ridx = i;
            it.energy += En[s];
            it.src.push_back(x);
            pen = true;
        }
        it.value = pen ? val[m] / 2 : val[m];
        for (int d : it.data) dsTake(d);
        for (auto &s : it.src) for (int d : s.data) dsTake(d);
        addItem(std::move(it));
    }
    fprintf(stderr, "solution initiale chargée : valeur %lld, énergie %.4f\n", curValue, (double)energyUsed / CAP);
}

// ------------------------------------------------------------------ recherche
static double elapsed(chrono::steady_clock::time_point t0) {
    return chrono::duration<double>(chrono::steady_clock::now() - t0).count();
}

static void greedyFill(const vector<int> &order) {
    for (int ci : order) {
        const Cand &c = cands[ci];
        if (En[c.m] > CAP - energyUsed) continue;
        tryInsert(c.m, c.alias);
    }
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: solver instance.txt sortie.json [k=v...]\n"); return 1; }
    P_out = argv[2];
    for (int i = 3; i < argc; i++) {
        string a = argv[i];
        auto p = a.find('=');
        string k = a.substr(0, p), v = a.substr(p + 1);
        if (k == "time") P_time = stod(v);
        else if (k == "seed") P_seed = stoi(v);
        else if (k == "wE") P_wE = stod(v);
        else if (k == "wD") P_wD = stod(v);
        else if (k == "wF") P_wF = stod(v);
        else if (k == "wV") P_wV = stod(v);
        else if (k == "alias") P_alias = stoi(v);
        else if (k == "sources") P_sources = stoi(v);
        else if (k == "pairLim") P_pairLim = stoi(v);
        else if (k == "srcTries") P_srcTries = stoi(v);
        else if (k == "kmin") P_kmin = stod(v);
        else if (k == "kmax") P_kmax = stod(v);
        else if (k == "T0") P_T0 = stod(v);
        else if (k == "noise") P_noise = stod(v);
        else if (k == "init") P_init = v;
        else if (k == "plan") P_plan = v;
        else if (k == "planBoost") P_planBoost = stod(v);
        else if (k == "planOrder") P_planOrder = stoi(v);
        else if (k == "aliasFirst") P_aliasFirst = stoi(v);
        else if (k == "halfCop") P_halfCop = stoi(v);
        else if (k == "tinyU") P_tinyU = stoi(v);
        else if (k == "hugeL") P_hugeL = stoi(v);
        else { fprintf(stderr, "option inconnue %s\n", k.c_str()); return 1; }
    }
    rng.seed(P_seed * 7919 + 17);

    FILE *f = fopen(argv[1], "r");
    if (fscanf(f, "%d %d %lld", &NM, &ND, &CAP) != 3) return 1;
    val.resize(NM); En.resize(NM); reqs.resize(NM);
    for (int m = 0; m < NM; m++) {
        int k;
        if (fscanf(f, "%d %lld %d", &val[m], &En[m], &k) != 3) return 1;
        reqs[m].resize(k);
        for (auto &r : reqs[m]) if (fscanf(f, "%d %d %d", &r.t, &r.L, &r.U) != 3) return 1;
    }
    dsT.resize(ND); dsS.resize(ND); dsC.resize(ND);
    for (int d = 0; d < ND; d++) {
        if (fscanf(f, "%d %d %d", &dsT[d], &dsS[d], &dsC[d]) != 3) return 1;
        MAXS = max(MAXS, dsS[d]);
    }
    fclose(f);

    avail.assign(ND, 0); stampv.assign(ND, 0);
    for (auto &p : pools) p.init();
    for (int d = 0; d < ND; d++) {
        dsAdd(d);
        supplyT[dsT[d]] += dsS[d];
        if (!dsC[d]) freeT[dsT[d]] += dsS[d];
    }
    totalV = 0;
    for (int m = 0; m < NM; m++) totalV += val[m];
    role.assign(NM, NONE); aliasOn.assign(NM, 0);
    itemOfModel.assign(NM, -1); itemOfAlias.assign(NM, -1);
    single.assign(NM, -1);
    srcList.assign(4, {});
    srcKey.assign(NM, 0);
    for (int m = 0; m < NM; m++) {
        if (reqs[m].size() != 1) continue;
        const Req &r = reqs[m][0];
        if (r.U < r.L) continue;
        single[m] = r.t;
        srcKey[m] = P_wE * (double)En[m] / CAP + P_wD * r.L / supplyT[r.t] + P_wV * val[m] / totalV +
                    1e-3 * r.L / supplyT[r.t];
        srcList[r.t].push_back(m);
    }
    if (!P_plan.empty()) {
        planFull.assign(NM, 0); planHalf.assign(NM, 0); planSrc.assign(NM, 0); planAlias.assign(NM, 0);
        planZ.assign(NM, {});
        ifstream in(P_plan);
        string line;
        while (getline(in, line)) {
            istringstream ls(line);
            int id; double x, y, sv, a;
            if (!(ls >> id >> x >> y >> sv >> a)) continue;
            planFull[id] = x > 0.5; planHalf[id] = y > 0.5; planSrc[id] = sv > 0.5; planAlias[id] = a > 0.5;
            double z;
            while (ls >> z) planZ[id].push_back(z > 0.5);
        }
        // sources prévues : en tête de liste
        for (int m = 0; m < NM; m++) if (planSrc[m] && single[m] >= 0) srcKey[m] -= 1e6;
    }
    for (int t = 0; t < 4; t++)
        sort(srcList[t].begin(), srcList[t].end(), [](int a, int b) { return srcKey[a] < srcKey[b]; });
    srcPos.assign(NM, -1);
    for (int t = 0; t < 4; t++) {
        srcPtr[t] = 0;
        for (int i = 0; i < (int)srcList[t].size(); i++) srcPos[srcList[t][i]] = i;
    }

    computePriorities();
    auto t0 = chrono::steady_clock::now();

    vector<int> order(cands.size());
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [](int a, int b) { return cands[a].prio > cands[b].prio; });
    // rang de chaque candidat pour les réparations
    vector<int> candOfModel(NM, -1), candOfAlias(NM, -1);
    for (int i = 0; i < (int)cands.size(); i++) (cands[i].alias ? candOfAlias : candOfModel)[cands[i].m] = i;

    if (!P_init.empty()) loadSolution(P_init);
    if (!planFull.empty() && P_init.empty()) {
        // construction du plan : pleins (gros besoins d'abord), puis moitiés, puis alias
        auto need = [](int m) { ll s = 0; for (auto &r : reqs[m]) s += r.L; return s; };
        vector<int> fulls, halves, aliases;
        for (int m = 0; m < NM; m++) {
            if (planFull[m]) fulls.push_back(m);
            else if (planHalf[m]) halves.push_back(m);
            if (planAlias[m]) aliases.push_back(m);
        }
        auto minU = [](int m) { int u = INT_MAX; for (auto &r : reqs[m]) u = min(u, r.U); return u; };
        auto byNeed = [&](vector<int> &v) {
            auto width = [](int m) { int w = INT_MAX; for (auto &r : reqs[m]) w = min(w, r.U - r.L); return w; };
            if (P_planOrder == 1) sort(v.begin(), v.end(), [&](int a, int b) { return minU(a) < minU(b); });
            else if (P_planOrder == 2) sort(v.begin(), v.end(), [&](int a, int b) { return width(a) < width(b); });
            else if (P_planOrder == 3) shuffle(v.begin(), v.end(), rng);
            else if (P_planOrder == 5) {
                // très gros besoins d'abord (besoin décroissant), puis petites fenêtres d'abord
                auto maxL = [](int m) { int l = 0; for (auto &r : reqs[m]) l = max(l, r.L); return l; };
                sort(v.begin(), v.end(), [&](int a, int b) {
                    bool ha = maxL(a) >= P_hugeL, hb = maxL(b) >= P_hugeL;
                    if (ha != hb) return ha;
                    if (ha) return need(a) > need(b);
                    return minU(a) < minU(b);
                });
            }
            else if (P_planOrder == 4) {
                // modèles ayant un besoin minuscule d'abord (par borne haute croissante), puis gros besoins
                sort(v.begin(), v.end(), [&](int a, int b) {
                    bool ta = minU(a) < P_tinyU, tb = minU(b) < P_tinyU;
                    if (ta != tb) return ta;
                    if (ta) return minU(a) < minU(b);
                    return need(a) > need(b);
                });
            }
            else sort(v.begin(), v.end(), [&](int a, int b) { return need(a) > need(b); });
        };
        byNeed(fulls); byNeed(halves);
        int okF = 0, okH = 0, okA = 0;
        if (P_aliasFirst) for (int m : aliases) okA += tryInsert(m, true, 2);
        for (int m : fulls) {
            bool ok = tryInsert(m, false, 1);
            okF += ok;
            if (!ok && getenv("DEBUG_PLAN")) {
                fprintf(stderr, "échec plein %d E=%lld :", m, En[m]);
                for (auto &r : reqs[m]) fprintf(stderr, " [t%d %d..%d libre=%lld]", r.t, r.L, r.U, pools[r.t * 2].units);
                fprintf(stderr, " énergie restante %.4f\n", (double)(CAP - energyUsed) / CAP);
            }
        }
        for (int m : halves) okH += tryInsert(m, false, 2);
        if (!P_aliasFirst) for (int m : aliases) okA += tryInsert(m, true, 2);
        fprintf(stderr, "plan : pleins %d/%zu, moitiés %d/%zu, alias %d/%zu -> valeur %lld énergie %.4f\n", okF,
                fulls.size(), okH, halves.size(), okA, aliases.size(), curValue, (double)energyUsed / CAP);
        for (int m : fulls) if (role[m] == NONE) tryInsert(m, false, 2);
    }
    greedyFill(order);
    ll bestValue = curValue;
    vector<Item> bestItems = items;
    writeSolution(P_out, bestItems);
    fprintf(stderr, "[%.1fs] glouton : valeur %lld énergie %.4f items %zu\n", elapsed(t0), curValue,
            (double)energyUsed / CAP, items.size() - freeSlots.size());

    // ------------------------------------------------------------ LNS
    double avgVal = 1;
    {
        double s = 0; int n = 0;
        for (auto &x : items) if (x.m >= 0) { s += x.value; n++; }
        if (n) avgVal = s / n;
    }
    double T0 = P_T0 >= 0 ? P_T0 : avgVal * 0.5;
    ll iter = 0, accepted = 0, improved = 0;
    double lastSave = 0, lastLog = 0;
    vector<int> active;
    vector<Item> removed;
    vector<int> inserted;
    vector<pair<double, int>> tryList;
    while (true) {
        double el = elapsed(t0);
        if (el > P_time) break;
        double frac = el / P_time;
        double T = T0 * pow(0.002, frac);
        iter++;
        active.clear();
        for (int i = 0; i < (int)items.size(); i++) if (items[i].m >= 0) active.push_back(i);
        if (active.empty()) break;
        int k = (int)(P_kmin + urand() * (P_kmax - P_kmin + 1));
        k = max(1, min(k, (int)active.size()));
        ll oldValue = curValue;
        removed.clear();
        // destruction : aléatoire, ou ciblée sur un type de données
        int mode = irand(4);
        int ty = irand(4);
        // mode 3 : un candidat non placé de forte priorité est inséré en premier, après avoir
        // retiré des modèles qui partagent ses types de données
        int target = -1, tmask = 0;
        if (mode == 3) {
            vector<int> top;
            for (int oi = 0; oi < (int)order.size() && (int)top.size() < 40; oi++) {
                const Cand &c = cands[order[oi]];
                bool used = c.alias ? aliasOn[c.m] : role[c.m] != NONE;
                if (!used) top.push_back(order[oi]);
            }
            if (!top.empty()) {
                target = top[irand(top.size())];
                for (auto &r : reqs[cands[target].m]) tmask |= 1 << r.t;
            } else mode = 0;
        }
        for (int j = 0; j < k && !active.empty(); j++) {
            int pick = -1;
            for (int a = 0; a < 6; a++) {
                int c = irand(active.size());
                int m = items[active[c]].m;
                bool hasT = false;
                for (auto &r : reqs[m]) hasT |= (mode == 3) ? ((tmask >> r.t) & 1) : r.t == ty;
                if ((mode != 1 && mode != 3) || hasT) { pick = c; break; }
                if (pick < 0) pick = c;
            }
            int idx = active[pick];
            active[pick] = active.back(); active.pop_back();
            removed.push_back(removeItem(idx));
        }
        // réparation : candidats bruités (meilleurs non utilisés + retirés + aléatoires)
        tryList.clear();
        int topTaken = 0;
        for (int oi = 0; oi < (int)order.size() && topTaken < 150; oi++) {
            const Cand &c = cands[order[oi]];
            bool used = c.alias ? aliasOn[c.m] : role[c.m] != NONE;
            if (used) continue;
            topTaken++;
            tryList.push_back({c.prio * exp(P_noise * 2 * (urand() - 0.5) * 2), order[oi]});
        }
        for (auto &x : removed) {
            int ci = x.alias ? candOfAlias[x.m] : candOfModel[x.m];
            if (ci >= 0) tryList.push_back({cands[ci].prio * exp(P_noise * 2 * (urand() - 0.5) * 2), ci});
        }
        for (int r = 0; r < 60; r++) {
            int ci = irand(cands.size());
            tryList.push_back({cands[ci].prio * exp(P_noise * 2 * (urand() - 0.5) * 2), ci});
        }
        if (target >= 0) tryList.push_back({1e300, target});
        sort(tryList.begin(), tryList.end(), [](auto &a, auto &b) { return a.first > b.first; });
        inserted.clear();
        for (auto &p : tryList) {
            const Cand &c = cands[p.second];
            if (En[c.m] > CAP - energyUsed) continue;
            if (tryInsert(c.m, c.alias)) inserted.push_back(c.alias ? itemOfAlias[c.m] : itemOfModel[c.m]);
        }
        ll delta = curValue - oldValue;
        if (delta >= 0 || urand() < exp(delta / max(1e-9, T))) {
            accepted++;
            if (curValue > bestValue) {
                bestValue = curValue;
                improved++;
                bestItems = items;
                if (el - lastSave > 20) { writeSolution(P_out, bestItems); lastSave = el; }
            }
        } else {
            for (int idx : inserted) removeItem(idx);
            for (auto &x : removed) restoreItem(x);
        }
        if (el - lastLog > 30) {
            fprintf(stderr, "[%.0fs] it %lld acc %lld best %lld cur %lld T %.2f énergie %.4f\n", el, iter,
                    accepted, bestValue, curValue, T, (double)energyUsed / CAP);
            lastLog = el;
        }
    }
    writeSolution(P_out, bestItems);
    fprintf(stderr, "fin : best %lld (courant %lld) itérations %lld\n", bestValue, curValue, iter);
    return 0;
}
