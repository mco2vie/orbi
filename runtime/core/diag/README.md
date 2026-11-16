# runtime/core/diag

Diagnostics: flight recorder, counters and profiling, RenderDoc, game phases and the census of SDK calls.

| File | What it is |
|---|---|
| `flight.c`, `flight.h`, `perf.c`, `prof*`, `perfmon.*`, `rdoc.c` | Diagnostics: flight recorder, counters, profiling, RenderDoc |
| `seqwatch.c` | `ORBITALS_SEQ_WATCH=1`: entries and exits of the game's phases (`seq: enter TitleMenuMain frame N`) through the function-entry hook of the translated code; the `seq` command of the control channel; `ORBITALS_SEQ_HOLD` holds the button script while a phase lasts; `ORBITALS_SEQ_UNTIL`/`ORBITALS_SEQ_EXIT`: goes off at a phase and exits N s later (`tools/run/race.sh`) |
| `impcensus.c` | `ORBITALS_IMPORT_CENSUS=<file>`: which SDK functions the game code calls during the run, how many times and from which frame, through the same entry hook as `seqwatch.c`; read by `tools/analisis/sdk_gaps.py --census` |
