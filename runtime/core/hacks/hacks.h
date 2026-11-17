// Hacks that the console does not have, for playing and above all for developing faster: each
// one off by default, with its ORBITALS_* key for the scripts and its row in the Hacks tab (ui/menu/settings_tabs.cpp).
#pragma once
#include <stdint.h>

// ---- turbo (turbo.c): the game runs `speed` times faster. ORBITALS_TURBO = off | hold | toggle (F2) | on | until,
// ORBITALS_TURBO_SPEED = 2..8. The present pacer and the vsync thread run `speed` times faster and the guest clock
// (rt_ticks) too, so the parts of the game that count frames and the parts that read the clock both speed up; the
// window shows at most 60 of those frames a second.
int turbo_speed(void);                     // the factor in effect now: 1 when off
void turbo_poll(void);                     // once per game present: the key and the settings
uint64_t turbo_clock(uint64_t real_ticks); // the guest clock for a host tick count (main.c rt_ticks)
uint64_t rt_ticks_real(void);              // main.c: the host's clock in guest ticks; rt_ticks is turbo_clock of it
int turbo_drop_present(uint64_t now_ns);   // 1: leave this frame out of the window (gfx_present.c)


// ---- fixed seed (seed.c): ORBITALS_SEED=<number> for the system's random entropy
int seed_random(uint64_t sub, uint64_t *out);   // svc.c GetInfo 11: 1 and *out when ORBITALS_SEED is set
int seed_time(int64_t *out);                    // ov_system.c: the clock with ORBITALS_SEED; 0 without it
uint64_t seed_tick(uint64_t lr);                // a seed patch set: the clock value the game seeds with at lr

// ---- freeze (freeze.c): F3 / F4 with ORBITALS_FREEZE_KEYS=1, or ctl pause | step [N] | resume
void freeze_set(int on, int64_t steps);  // on: stop after `steps` more frames
void freeze_present(void);               // the game's present: waits while frozen

