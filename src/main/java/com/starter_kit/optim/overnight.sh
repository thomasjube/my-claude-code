#!/bin/bash
# Boucle d'optimisation longue : 4 recherches en parallèle par tour, puis commit/push des améliorations.
# Usage : WORK=<dossier de travail> overnight.sh <secondes par tour>
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${WORK:-/tmp/rubik_contest}
T=${1:-1800}
REPO=$(cd "$HERE/../../../../../.." && pwd)
plan() { case $1 in
    2_medium) echo "plan=$WORK/mip/2_fs1.txt";; 3_free) echo "plan=$WORK/mip/3_free.txt";;
    4_precise) echo "plan=$WORK/mip/4_precise.txt";; 5_energy) echo "plan=$WORK/mip/5_energy.txt";;
    6_shortage) echo "plan=$WORK/mip/6_shortage.txt";; 7_big) echo "plan=$WORK/mip/7_lp.txt";; esac; }
ROUNDS=("6_shortage 6_shortage 7_big 5_energy" "6_shortage 2_medium 4_precise 7_big" "6_shortage 5_energy 3_free 2_medium")
r=0
while true; do
    set -- ${ROUNDS[$((r % ${#ROUNDS[@]}))]}
    i=0
    for inst in "$@"; do
        seed=$((r * 10 + i)); i=$((i + 1))
        kmax=$((10 + (seed * 7) % 40))
        alias=1; [ "$inst" = 4_precise ] && alias=0
        WORK=$WORK "$HERE/run_long.sh" "$inst" "$T" "$seed" alias=$alias $(plan "$inst") T0=0.3 pairLim=60 \
            kmax=$kmax >> "$WORK/overnight.log" 2>&1 &
        sleep 5
    done
    wait
    r=$((r + 1))
    cd "$REPO"
    if ! git diff --quiet -- src/main/java/com/starter_kit/solutions; then
        git add src/main/java/com/starter_kit/solutions
        git commit -q -m "Concours : améliorations nocturnes (tour $r)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_018uDEok5VDKqYEAsNQ58Jvc"
        for k in 1 2 3 4; do git push -q origin claude/ecstatic-gauss-eqwmy1 && break; sleep $((2 ** k)); done
    fi
    echo "tour $r terminé $(date)" >> "$WORK/overnight.log"
done
