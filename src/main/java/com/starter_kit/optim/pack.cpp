// Réalisation d'un plan MILP : affectation des datasets aux besoins par recherche locale.
//
// Usage : pack <instance.txt> <plan.txt> <sortie.txt> [time=s] [seed=n]
//
// Pour chaque type de données, chaque besoin à remplir par des datasets devient un groupe
// [L, U] (datasets libres uniquement pour les modèles « pleins »). On minimise la somme des
// violations (manque sous L + excès au-dessus de U) par déplacements / échanges de datasets.
// Les modèles dont un groupe reste violé sont retirés. Les besoins sourcés reçoivent une source
// prévue du même type. Sortie au format texte : « D dataset modèle » et « M source cible ».
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int NM, ND;
ll CAP;
struct Req { int t, L, U; };
vector<int> val;
vector<ll> En;
vector<vector<Req>> reqs;
vector<int> dsT, dsS, dsC;
mt19937_64 rng(1);
static inline double urand() { return (rng() >> 11) * (1.0 / 9007199254740992.0); }
static inline int irand(int n) { return (int)(rng() % (unsigned long long)n); }

struct Group { int model; int t; int L, U; bool freeOnly; ll sum; vector<int> ds; };

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: pack instance plan sortie [time=] [seed=]\n"); return 1; }
    double timeLimit = 30;
    for (int i = 4; i < argc; i++) {
        string a = argv[i];
        auto p = a.find('=');
        if (a.substr(0, p) == "time") timeLimit = stod(a.substr(p + 1));
        if (a.substr(0, p) == "seed") rng.seed(stoi(a.substr(p + 1)));
    }
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
    for (int d = 0; d < ND; d++) if (fscanf(f, "%d %d %d", &dsT[d], &dsS[d], &dsC[d]) != 3) return 1;
    fclose(f);

    // plan
    vector<char> full(NM, 0), half(NM, 0), src(NM, 0), ali(NM, 0);
    vector<vector<char>> z(NM);
    {
        ifstream in(argv[2]);
        string line;
        while (getline(in, line)) {
            istringstream ls(line);
            int id; double x, y, s, a;
            if (!(ls >> id >> x >> y >> s >> a)) continue;
            full[id] = x > 0.5; half[id] = y > 0.5; src[id] = s > 0.5; ali[id] = a > 0.5;
            double v;
            while (ls >> v) z[id].push_back(v > 0.5);
        }
    }
    // groupes de datasets et besoins sourcés, par type
    vector<Group> groups;
    vector<vector<int>> slots(4), sources(4);  // slots : cibles (id brut) ; sources : modèles
    for (int m = 0; m < NM; m++) {
        if (full[m] || half[m]) {
            for (int k = 0; k < (int)reqs[m].size(); k++) {
                const Req &r = reqs[m][k];
                if (half[m] && k < (int)z[m].size() && z[m][k]) slots[r.t].push_back(m);
                else groups.push_back({m, r.t, r.L, r.U, (bool)full[m], 0, {}});
            }
        }
        if (src[m]) {
            const Req &r = reqs[m][0];
            groups.push_back({m, r.t, r.L, r.U, false, 0, {}});
            sources[r.t].push_back(m);
        }
        if (ali[m]) for (auto &r : reqs[m]) slots[r.t].push_back(m - NM);
    }
    fprintf(stderr, "groupes %zu\n", groups.size());

    vector<int> owner(ND, -1);  // groupe propriétaire
    vector<char> dropM(NM, 0);  // modèles sacrifiés pendant la réalisation
    vector<char> dead(groups.size(), 0);
    auto viol = [&](const Group &g) -> ll { return max<ll>(0, g.L - g.sum) + max<ll>(0, g.sum - g.U); };
    auto t0 = chrono::steady_clock::now();
    auto elapsed = [&]() { return chrono::duration<double>(chrono::steady_clock::now() - t0).count(); };

    for (int t = 0; t < 4; t++) {
        vector<int> G;
        for (int g = 0; g < (int)groups.size(); g++)
            if (groups[g].t == t && !dropM[groups[g].model]) G.push_back(g);
        vector<int> DS;
        for (int d = 0; d < ND; d++) if (dsT[d] == t) DS.push_back(d);
        // index des datasets non affectés par (libre, taille)
        int MAXS = 0;
        for (int d : DS) MAXS = max(MAXS, dsS[d]);
        vector<vector<vector<int>>> freeBk(2, vector<vector<int>>(MAXS + 1));
        vector<int> pos(ND, -1);
        auto unassignAdd = [&](int d) { auto &b = freeBk[dsC[d]][dsS[d]]; pos[d] = b.size(); b.push_back(d); };
        auto unassignDel = [&](int d) {
            auto &b = freeBk[dsC[d]][dsS[d]];
            int p = pos[d], last = b.back();
            b[p] = last; pos[last] = p; b.pop_back(); pos[d] = -1;
        };
        for (int d : DS) unassignAdd(d);
        // recherche d'un dataset non affecté de taille dans [lo, hi] (libre seulement si freeOnly)
        auto findUn = [&](ll lo, ll hi, bool freeOnly, bool preferCop) -> int {
            lo = max<ll>(lo, 1); hi = min<ll>(hi, MAXS);
            if (lo > hi) return -1;
            // essai aléatoire puis balayage
            int order[2] = {preferCop ? 1 : 0, preferCop ? 0 : 1};
            for (int oi = 0; oi < 2; oi++) {
                int c = order[oi];
                if (freeOnly && c == 1) continue;
                for (ll s = lo; s <= hi; s++) if (!freeBk[c][s].empty()) return freeBk[c][s][irand(freeBk[c][s].size())];
            }
            return -1;
        };
        auto assign = [&](int d, int g) { unassignDel(d); owner[d] = g; groups[g].ds.push_back(d); groups[g].sum += dsS[d]; };
        auto unassign = [&](int d) {
            int g = owner[d];
            auto &v = groups[g].ds;
            v.erase(find(v.begin(), v.end(), d));
            groups[g].sum -= dsS[d];
            owner[d] = -1;
            unassignAdd(d);
        };
        // construction gloutonne : groupes « libres seulement » d'abord, puis par L décroissant
        sort(G.begin(), G.end(), [&](int a, int b) {
            if (groups[a].freeOnly != groups[b].freeOnly) return groups[a].freeOnly > groups[b].freeOnly;
            return groups[a].L > groups[b].L;
        });
        for (int g : G) {
            Group &gr = groups[g];
            while (gr.sum < gr.L) {
                ll R = gr.L - gr.sum, room = gr.U - gr.sum;
                int d = findUn(R, min<ll>(room, R + 0), gr.freeOnly, true);
                if (d < 0) d = findUn(R, room, gr.freeOnly, true);
                if (d >= 0) { assign(d, g); break; }
                // plus gros dataset < R
                int best = -1;
                for (int c = 0; c < 2 && best < 0; c++) {
                    int cc = gr.freeOnly ? 0 : (c == 0 ? 1 : 0);
                    if (gr.freeOnly && c == 1) break;
                    for (ll s = min<ll>(R - 1, MAXS); s >= 1; s--) if (!freeBk[cc][s].empty()) { best = freeBk[cc][s].back(); break; }
                }
                if (best < 0) break;
                assign(best, g);
            }
        }
        // recherche locale sur les violations
        ll total = 0;
        for (int g : G) total += viol(groups[g]);
        fprintf(stderr, "type %d : %zu groupes, violation initiale %lld\n", t, G.size(), total);
        double tEnd = elapsed() + timeLimit / 4;
        vector<int> bad;
        ll it = 0, lastImp = 0, bestTot = total;
        int sacrificed = 0;
        while (total > 0 && elapsed() < tEnd) {
            if (it - lastImp > 300000) {
                // stagnation : sacrifier le modèle violé le moins précieux
                int victim = -1; double vv = 1e18;
                for (int g : G) if (viol(groups[g]) > 0) {
                    int m = groups[g].model;
                    double cost = src[m] ? 1e9 : (full[m] ? val[m] : val[m] / 2.0);
                    if (cost < vv) { vv = cost; victim = g; }
                }
                if (victim < 0) break;
                Group &vg = groups[victim];
                total -= viol(vg);
                while (!vg.ds.empty()) unassign(vg.ds.back());
                dropM[vg.model] = 1;
                G.erase(find(G.begin(), G.end(), victim));
                sacrificed++;
                lastImp = it; bestTot = total;
                bad.clear();
                continue;
            }
            if ((it & 1023) == 0 || bad.empty()) {
                bad.clear();
                for (int g : G) if (viol(groups[g]) > 0) bad.push_back(g);
                if (bad.empty()) break;
            }
            if (total < bestTot) { bestTot = total; lastImp = it; }
            it++;
            // compaction : un groupe au-dessus de L échange un dataset contre un plus petit non affecté
            if (irand(3) == 0) {
                int h = G[irand(G.size())];
                Group &hr = groups[h];
                ll slack = hr.sum - hr.L;
                if (slack > 0 && slack <= hr.U - hr.L && !hr.ds.empty()) {
                    int a = hr.ds[irand(hr.ds.size())];
                    int b = findUn(max<ll>(1, dsS[a] - slack), dsS[a] - 1, hr.freeOnly, true);
                    if (b >= 0) { unassign(a); assign(b, h); }
                }
            }
            int g = bad[irand(bad.size())];
            Group &gr = groups[g];
            ll v0 = viol(gr);
            if (v0 == 0) continue;
            if (gr.sum < gr.L && !gr.ds.empty() && irand(2) == 0) {
                // échange avec un dataset non affecté plus grand : a -> b, b - a dans [R, room]
                ll R0 = gr.L - gr.sum, room0 = gr.U - gr.sum;
                int a = gr.ds[irand(gr.ds.size())];
                int b = findUn(dsS[a] + R0, dsS[a] + room0, gr.freeOnly, true);
                if (b >= 0) { unassign(a); assign(b, g); total -= v0; continue; }
            }
            ll R = gr.L - gr.sum;   // > 0 : manque ; sinon excès = sum - U
            int mv = irand(4);
            if (R > 0) {
                ll room = gr.U - gr.sum;
                if (mv == 0) {
                    int d = findUn(R, room, gr.freeOnly, true);
                    if (d >= 0) { assign(d, g); total -= v0; continue; }
                }
                // prendre un dataset d'un autre groupe h qui reste faisable
                int h = G[irand(G.size())];
                if (h == g || groups[h].ds.empty()) continue;
                Group &hr = groups[h];
                int d = hr.ds[irand(hr.ds.size())];
                if (gr.freeOnly && dsC[d]) continue;
                if (mv <= 1) {
                    // déplacement d : h -> g
                    ll vh0 = viol(hr);
                    ll gs = gr.sum + dsS[d], hs = hr.sum - dsS[d];
                    ll vg1 = max<ll>(0, gr.L - gs) + max<ll>(0, gs - gr.U);
                    ll vh1 = max<ll>(0, hr.L - hs) + max<ll>(0, hs - hr.U);
                    ll delta = vg1 + vh1 - v0 - vh0;
                    if (delta <= 0) {
                        unassign(d); assign(d, g); total += delta;
                    }
                } else {
                    // échange d (h) <-> e (g)
                    if (gr.ds.empty()) continue;
                    int e = gr.ds[irand(gr.ds.size())];
                    if (hr.freeOnly && dsC[e]) continue;
                    ll vh0 = viol(hr);
                    ll diff = dsS[d] - dsS[e];
                    ll gs = gr.sum + diff, hs = hr.sum - diff;
                    ll vg1 = max<ll>(0, gr.L - gs) + max<ll>(0, gs - gr.U);
                    ll vh1 = max<ll>(0, hr.L - hs) + max<ll>(0, hs - hr.U);
                    ll delta = vg1 + vh1 - v0 - vh0;
                    if (delta <= 0) {
                        unassign(d); unassign(e); assign(d, g); assign(e, h); total += delta;
                    }
                }
            } else {
                // excès : retirer ou échanger contre un plus petit non affecté
                ll ex = gr.sum - gr.U;
                if (gr.ds.empty()) continue;
                int d = gr.ds[irand(gr.ds.size())];
                if (mv <= 1 && dsS[d] >= ex && gr.sum - dsS[d] >= gr.L) { unassign(d); total -= v0; continue; }
                int e = findUn(dsS[d] - (gr.sum - gr.L), dsS[d] - ex, gr.freeOnly, true);
                if (e >= 0) {
                    unassign(d); assign(e, g); total -= v0;
                }
            }
        }
        fprintf(stderr, "type %d : violation finale %lld (%lld itérations, %d sacrifiés)\n", t, total, it, sacrificed);
        for (int g : G) if (viol(groups[g]) > 0) dead[g] = 1;
    }
    // modèles à retirer : groupe violé
    vector<char> drop(NM, 0), dropAlias(NM, 0);
    for (int g = 0; g < (int)groups.size(); g++) if (dead[g]) drop[groups[g].model] = 1;
    for (int m = 0; m < NM; m++) if (dropM[m]) drop[m] = 1;
    // sources : un modèle source retiré ne peut plus servir ; affectation slots <- sources
    ll value = 0, energy = 0;
    vector<pair<int, int>> mm;
    for (int t = 0; t < 4; t++) {
        vector<int> avail;
        for (int s : sources[t]) if (!drop[s]) avail.push_back(s);
        for (int raw : slots[t]) {
            int m = raw < 0 ? raw + NM : raw;
            bool isAlias = raw < 0;
            if (isAlias ? dropAlias[m] : drop[m]) continue;
            if (avail.empty()) { if (isAlias) dropAlias[m] = 1; else drop[m] = 1; continue; }
            mm.push_back({avail.back(), raw});
            avail.pop_back();
        }
    }
    // une cible retirée libère ses sources : on retire les correspondances (sources inutilisées)
    vector<pair<int, int>> mm2;
    vector<char> srcUsed(NM, 0);
    for (auto &p : mm) {
        int m = p.second < 0 ? p.second + NM : p.second;
        bool dropped = p.second < 0 ? dropAlias[m] : drop[m];
        if (!dropped) { mm2.push_back(p); srcUsed[p.first] = 1; }
    }
    FILE *o = fopen(argv[3], "w");
    int nF = 0, nH = 0, nA = 0;
    for (int g = 0; g < (int)groups.size(); g++) {
        const Group &gr = groups[g];
        int m = gr.model;
        bool keep = src[m] ? srcUsed[m] && !drop[m] : !drop[m];
        if (!keep) continue;
        for (int d : gr.ds) fprintf(o, "D %d %d\n", d, m);
    }
    for (auto &p : mm2) fprintf(o, "M %d %d\n", p.first, p.second);
    fclose(o);
    for (int m = 0; m < NM; m++) {
        if ((full[m] || half[m]) && !drop[m]) {
            if (full[m]) { value += val[m]; nF++; } else { value += val[m] / 2; nH++; }
            energy += En[m];
        }
        if (ali[m] && !dropAlias[m]) { value += val[m] / 2; energy += En[m]; nA++; }
        if (src[m] && srcUsed[m] && !drop[m]) energy += En[m];
    }
    fprintf(stderr, "réalisé : pleins %d, moitiés %d, alias %d, valeur estimée %lld, énergie %.4f\n", nF, nH, nA,
            value, (double)energy / CAP);
    return 0;
}
