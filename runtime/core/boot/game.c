// The game clock the shared runtime reads (host.h frame_step_*): counted from presents, and for the A/B blocks from
// the phase ORBITALS_SEQ_UNTIL waits for. totk-pc-recomp's resolution.c and frame_rate.c (patch sites and fixed addresses
// of TotK) have no counterpart here yet: a frame-rate setting needs the game's own frame object, not found for
// Orbitals (runtime/core/boot/version.c).
#include <stdatomic.h>

#include "host.h"

static _Atomic uint64_t ticks;   // 60 Hz ticks since the first present

// No save-load point: the A/B blocks (ORBITALS_AB, perf.c rt_ab) count from the phase ORBITALS_SEQ_UNTIL waits for, so both
// halves measure the same scene.
int64_t frame_step_world_us(void) { return seqwatch_since_us(); }

uint64_t frame_step_ticks(void) { return atomic_load_explicit(&ticks, memory_order_relaxed); }

void frame_step_present(uint64_t display_ns, int interval) {
    (void)display_ns;
    atomic_fetch_add_explicit(&ticks, interval > 0 ? (uint64_t)interval : 1, memory_order_relaxed);
}
