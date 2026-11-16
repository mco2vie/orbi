#!/usr/bin/env bash
# A race run: menu presses until the race, then run_perf.sh. The phase watch (ORBITALS_SEQ_WATCH) finds the race's start
# (the first IsSequenceFlag after the cup movie) and goes off there (ORBITALS_SEQ_UNTIL), so the race is measured without
# its cost; the run ends RACE_SECS (default 20) s later (ORBITALS_SEQ_EXIT), with the ORBITALS_HOST_TIME census of that window.
# SECONDS is only the safety limit.
# Usage: race.sh NAME [SECONDS]; extra env (ORBITALS_*, ORBITALS_DUMP...) passes through.
set -euo pipefail
cd "$(dirname "$0")/../.."
# Refuse a stale build/orbitals-recomp: a runtime source newer than it means the last build did not run or failed (01/11/2026:
# three runs measured the previous binary after a commit hook stopped the build and a compile error went unseen).
if [ -n "$(find runtime -newer build/orbitals-recomp \( -name '*.c' -o -name '*.h' -o -name '*.cpp' \) -print -quit)" ]; then
  echo "${0##*/}: runtime/ is newer than build/orbitals-recomp: build first (tools/build/build.py)" >&2; exit 1
fi
export ORBITALS_INPUT_SCRIPT=${ORBITALS_INPUT_SCRIPT:-tools/run/press-race.txt}
export ORBITALS_SPARSE_MIB=${ORBITALS_SPARSE_MIB:-768}
export ORBITALS_SEQ_WATCH=${ORBITALS_SEQ_WATCH:-1} ORBITALS_SEQ_UNTIL=${ORBITALS_SEQ_UNTIL--WaitIntroMovie,IsSequenceFlag} ORBITALS_SEQ_EXIT=${ORBITALS_SEQ_EXIT-${RACE_SECS:-20}}
# The world clock starts with the race: --seconds must not end the run before ORBITALS_SEQ_EXIT (01/11/2026: RACE_SECS=48
# runs ended at 18-28 s on run_perf.sh's default 30).
# The way to the race at turbo speed with the cup movie skipped (core/hacks): the turbo goes off at ORBITALS_SEQ_UNTIL's
# event, so the race itself runs at normal speed. ORBITALS_TURBO=off for the menus as the player sees them.
export ORBITALS_TURBO=${ORBITALS_TURBO:-until}
export WORLD_SECS=${WORLD_SECS:-$(( ${RACE_SECS:-20} + 30 ))}
export ORBITALS_FLIGHT=${ORBITALS_FLIGHT:-1} ORBITALS_FLIGHT_SPIKE_MS=${ORBITALS_FLIGHT_SPIKE_MS:-0} ORBITALS_FLIGHT_AT=${ORBITALS_FLIGHT_AT:-2000,2700,2900,3000}
exec tools/run/run_perf.sh "$1" "${2:-240}"
