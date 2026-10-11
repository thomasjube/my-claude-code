// Empaquetage exact des datasets libres pour les modèles « pleins » d'un plan, type par type, par recuit simulé.
//
// Usage : fpack <instance.txt> <plan.txt> <sortie.txt> [time=s par type] [seed=n] [T0=x]
//
// Pour chaque type t : groupes = besoins de type t des modèles pleins du plan, datasets = libres de type t.
// Pénalité = somme des manques sous L et excès au-dessus de U. Mouvements : ajout / retrait / échange avec le
// réservoir (datasets non affectés), déplacement et échange entre groupes ; compaction des groupes en excès de
// volume. Si une pénalité subsiste, les modèles violés de plus faible valeur sont retirés (tous types).
// Sortie : lignes « D dataset modèle » des modèles réalisés dans tous leurs types.
#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int NM, ND; ll CAP;
struct Req { int t, L, U; };
vector<int> val; vector<ll> En; vector<vector<Req>> reqs;
vector<int> dsT, dsS, dsC;
mt19937_64 rng(1);
static inline double urand() { return (rng() >> 11) * (1.0 / 9007199254740992.0); }
static inline int irand(int n) { return (int)(rng() % (unsigned long long)n); }

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: fpack instance plan sortie [time=] [seed=] [T0=]\n"); return 1; }
    double tPer = 60, T0 = 20, SLICE = 0.25;
    for (int i = 4; i < argc; i++) {
        string a = argv[i]; auto p = a.find('=');
        string k = a.substr(0, p), v = a.substr(p + 1);
        if (k == "time") tPer = stod(v);
        if (k == "seed") rng.seed(stoi(v));
        if (k == "T0") T0 = stod(v);
        if (k == "slice") SLICE = stod(v);
    }
    FILE *f = fopen(argv[1], "r");
    if (fscanf(f, "%d %d %lld", &NM, &ND, &CAP) != 3) return 1;
    val.resize(NM); En.resize(NM); reqs.resize(NM);
    for (int m = 0; m < NM; m++) {
        int k; if (fscanf(f, "%d %lld %d", &val[m], &En[m], &k) != 3) return 1;
        reqs[m].resize(k);
        for (auto &r : reqs[m]) if (fscanf(f, "%d %d %d", &r.t, &r.L, &r.U) != 3) return 1;
    }
    dsT.resize(ND); dsS.resize(ND); dsC.resize(ND);
    for (int d = 0; d < ND; d++) if (fscanf(f, "%d %d %d", &dsT[d], &dsS[d], &dsC[d]) != 3) return 1;
    fclose(f);
    vector<char> full(NM, 0);
    { ifstream in(argv[2]); string line;
      while (getline(in, line)) { istringstream ls(line); int id; double x; if (ls >> id >> x) full[id] = x > 0.5; } }
    vector<char> drop(NM, 0);
    vector<int> owner(ND, -1);  // modèle propriétaire (datasets libres)
    int MAXS = 0; for (int d = 0; d < ND; d++) MAXS = max(MAXS, dsS[d]);

    for (int t = 0; t < 4; t++) {
        // groupes
        vector<int> gm; vector<ll> gL, gU;
        for (int m = 0; m < NM; m++) if (full[m] && !drop[m])
            for (auto &r : reqs[m]) if (r.t == t) { gm.push_back(m); gL.push_back(r.L); gU.push_back(r.U); }
        int G = gm.size();
        vector<int> DS; for (int d = 0; d < ND; d++) if (dsT[d] == t && !dsC[d]) DS.push_back(d);
        vector<int> grp(ND, -2);  // -1 réservoir, >= 0 groupe
        vector<vector<int>> gds(G); vector<int> pos(ND, -1); vector<ll> sum(G, 0);
        vector<vector<int>> bk(MAXS + 1); vector<int> bpos(ND, -1);
        auto poolAdd = [&](int d) { grp[d] = -1; bpos[d] = bk[dsS[d]].size(); bk[dsS[d]].push_back(d); };
        auto poolDel = [&](int d) { auto &b = bk[dsS[d]]; int p = bpos[d], l = b.back(); b[p] = l; bpos[l] = p; b.pop_back(); bpos[d] = -1; };
        auto gAdd = [&](int d, int g) { grp[d] = g; pos[d] = gds[g].size(); gds[g].push_back(d); sum[g] += dsS[d]; };
        auto gDel = [&](int d) { int g = grp[d]; auto &v = gds[g]; int p = pos[d], l = v.back(); v[p] = l; pos[l] = p; v.pop_back(); sum[g] -= dsS[d]; };
        auto toGroup = [&](int d, int g) { if (grp[d] == -1) poolDel(d); else if (grp[d] >= 0) gDel(d); gAdd(d, g); };
        auto toPool = [&](int d) { if (grp[d] >= 0) gDel(d); poolAdd(d); };
        auto pen = [&](int g, ll s) -> ll { return max<ll>(0, gL[g] - s) + max<ll>(0, s - gU[g]); };
        auto findPool = [&](ll lo, ll hi) -> int {
            lo = max<ll>(lo, 1); hi = min<ll>(hi, MAXS);
            if (lo > hi) return -1;
            ll s0 = lo + irand((int)(hi - lo + 1));
            for (ll s = s0; s <= hi; s++) if (!bk[s].empty()) return bk[s][irand(bk[s].size())];
            for (ll s = s0 - 1; s >= lo; s--) if (!bk[s].empty()) return bk[s][irand(bk[s].size())];
            return -1;
        };
        for (int d : DS) poolAdd(d);
        // construction : L décroissant, meilleur ajustement
        vector<int> ord(G); iota(ord.begin(), ord.end(), 0);
        sort(ord.begin(), ord.end(), [&](int a, int b) { return gL[a] > gL[b]; });
        for (int g : ord) {
            while (sum[g] < gL[g]) {
                ll R = gL[g] - sum[g], room = gU[g] - sum[g];
                int d = -1;
                for (ll s = R; s <= min<ll>(room, MAXS) && d < 0; s++) if (!bk[s].empty()) d = bk[s].back();
                if (d >= 0) { toGroup(d, g); break; }
                for (ll s = min<ll>(R - 1, MAXS); s >= 1 && d < 0; s--) if (!bk[s].empty()) d = bk[s].back();
                if (d < 0) break;
                toGroup(d, g);
            }
        }
        ll total = 0; for (int g = 0; g < G; g++) total += pen(g, sum[g]);
        fprintf(stderr, "type %d : %d groupes, %zu datasets libres, pénalité initiale %lld\n", t, G, DS.size(), total);
        auto t0 = chrono::steady_clock::now();
        auto el = [&]() { return chrono::duration<double>(chrono::steady_clock::now() - t0).count(); };
        vector<int> bad; ll it = 0; ll best = total;
        double T = T0, slice = tPer * SLICE, sStart = 0;
        vector<char> gdead(G, 0);
        int sacr = 0;
        while (total > 0) {
            if ((it & 4095) == 0) {
                double e = el(); if (e > tPer) break;
                if (e - sStart > slice) {
                    // sacrifice : le groupe violé du modèle de plus faible valeur
                    int v = -1;
                    for (int g = 0; g < G; g++) if (!gdead[g] && pen(g, sum[g]) > 0 && (v < 0 || val[gm[g]] < val[gm[v]])) v = g;
                    if (v < 0) break;
                    int m = gm[v];
                    for (int g = 0; g < G; g++) if (gm[g] == m) {
                        total -= pen(g, sum[g]);
                        while (!gds[g].empty()) toPool(gds[g].back());
                        gdead[g] = 1; gL[g] = 0; gU[g] = 0;
                    }
                    drop[m] = 1; sacr++; sStart = e;
                    fprintf(stderr, "  [%.0fs] sacrifice %d (v=%d), pénalité %lld\n", e, m, val[m], total);
                    if (total <= 0) break;
                }
                T = T0 * pow(0.01, (e - sStart) / slice);
                bad.clear(); for (int g = 0; g < G; g++) if (pen(g, sum[g]) > 0) bad.push_back(g);
                if (bad.empty()) break;
            }
            it++;
            int g = (irand(4) == 0) ? irand(G) : bad[irand(bad.size())];
            if (gdead[g]) continue;
            ll R = gL[g] - sum[g], room = gU[g] - sum[g];
            ll p0 = pen(g, sum[g]);
            int mv = irand(8);
            if (mv == 0) {
                // compaction d'un groupe quelconque : a -> plus petit du réservoir, reste >= L
                int h = irand(G); if (gdead[h]) continue; ll sl = sum[h] - gL[h];
                if (sl <= 0 || gds[h].empty() || sum[h] > gU[h]) continue;
                int a = gds[h][irand(gds[h].size())];
                int b = findPool(dsS[a] - sl, dsS[a] - 1);
                if (b >= 0) { toPool(a); toGroup(b, h); }
                continue;
            }
            if (R > 0 && mv <= 2) {
                // ajout depuis le réservoir (exact si possible, sinon partiel)
                int d = findPool(R, room);
                if (d < 0 && mv == 2) d = findPool(1, R - 1);
                if (d < 0) continue;
                ll p1 = pen(g, sum[g] + dsS[d]);
                ll delta = p1 - p0;
                if (delta <= 0 || urand() < exp(-delta / T)) { toGroup(d, g); total += delta; }
                continue;
            }
            if (R > 0 && mv == 3 && !gds[g].empty()) {
                // échange a (g) -> b (réservoir) plus grand
                int a = gds[g][irand(gds[g].size())];
                int b = findPool(dsS[a] + R, dsS[a] + room);
                if (b < 0) b = findPool(dsS[a] + 1, dsS[a] + R - 1);
                if (b < 0) continue;
                ll p1 = pen(g, sum[g] - dsS[a] + dsS[b]); ll delta = p1 - p0;
                if (delta <= 0 || urand() < exp(-delta / T)) { toPool(a); toGroup(b, g); total += delta; }
                continue;
            }
            if (R < 0 && sum[g] > gU[g] && mv <= 3 && !gds[g].empty()) {
                // excès : retirer ou échanger contre un plus petit
                int a = gds[g][irand(gds[g].size())];
                ll ex = sum[g] - gU[g];
                if (mv <= 2) { ll p1 = pen(g, sum[g] - dsS[a]); ll delta = p1 - p0;
                    if (delta <= 0 || urand() < exp(-delta / T)) { toPool(a); total += delta; } continue; }
                int b = findPool(dsS[a] - ex - (gU[g] - gL[g]), dsS[a] - ex);
                if (b < 0) continue;
                ll p1 = pen(g, sum[g] - dsS[a] + dsS[b]); ll delta = p1 - p0;
                if (delta <= 0 || urand() < exp(-delta / T)) { toPool(a); toGroup(b, g); total += delta; }
                continue;
            }
            // entre groupes : déplacement d (h -> g) ou échange d (h) <-> e (g)
            int h = irand(G); if (h == g || gds[h].empty() || gdead[h]) continue;
            int d = gds[h][irand(gds[h].size())];
            ll ph0 = pen(h, sum[h]);
            if (irand(2) == 0 || gds[g].empty()) {
                ll delta = pen(g, sum[g] + dsS[d]) + pen(h, sum[h] - dsS[d]) - p0 - ph0;
                if (delta <= 0 || urand() < exp(-delta / T)) { gDel(d); gAdd(d, g); total += delta; }
            } else {
                int e = gds[g][irand(gds[g].size())];
                ll df = dsS[d] - dsS[e];
                ll delta = pen(g, sum[g] + df) + pen(h, sum[h] - df) - p0 - ph0;
                if (delta <= 0 || urand() < exp(-delta / T)) { gDel(d); gDel(e); gAdd(d, g); gAdd(e, h); total += delta; }
            }
            if (total < best) best = total;
        }
        // retrait des modèles violés
        int nd = 0;
        for (int g = 0; g < G; g++) if (pen(g, sum[g]) > 0 && !drop[gm[g]]) { drop[gm[g]] = 1; nd++; }
        for (int g = 0; g < G; g++) if (!drop[gm[g]]) for (int d : gds[g]) owner[d] = gm[g];
        fprintf(stderr, "type %d : pénalité finale %lld, %lld itérations, %d sacrifiés, %d retirés à la fin\n", t, total, it, sacr, nd);
    }
    FILE *o = fopen(argv[3], "w");
    int nf = 0; ll v = 0;
    for (int d = 0; d < ND; d++) if (owner[d] >= 0 && !drop[owner[d]]) fprintf(o, "D %d %d\n", d, owner[d]);
    for (int m = 0; m < NM; m++) if (full[m] && !drop[m]) { nf++; v += val[m]; }
    fclose(o);
    fprintf(stderr, "pleins réalisés %d, valeur %lld\n", nf, v);
}
