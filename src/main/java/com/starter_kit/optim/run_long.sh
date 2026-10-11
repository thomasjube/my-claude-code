#!/bin/bash
# Optimisation longue d'une instance en repartant de la meilleure solution connue.
# Usage : run_long.sh <instance> <secondes> <graine> [options solveur...]
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=${WORK:-/tmp/rubik_contest}
INST=$1; T=$2; SEED=$3; shift 3
mkdir -p "$WORK/out"
python3 "$HERE/sol2txt.py" "$HERE/../solutions/${INST}_submission.json" "$WORK/out/${INST}_init_$SEED.txt"
OUT="$WORK/out/${INST}_long_$SEED.json"
( ulimit -v 4000000; timeout $((T + 120)) "$WORK/solver" "$WORK/inst/$INST.txt" "$OUT" time=$T seed=$SEED \
    init="$WORK/out/${INST}_init_$SEED.txt" "$@" 2> "$WORK/out/${INST}_long_$SEED.log" )
python3 "$HERE/keep_best.py" "$INST" "$OUT"
