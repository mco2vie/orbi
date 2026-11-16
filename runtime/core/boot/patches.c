// Code patch sets (recomp/patches.py, gen.py --patches). The generator lifts both the original and the replacement
// instructions of every patched site, and rt_patch_on[set] picks one when the site runs, so a set is switched at start
// without touching code, and also while the game runs (rt_patch_switch). The sets, their environment switches and
// defaults, and the patch page come from the game code's tables (gamelib.h, from the generated patches.h); without
// them (C generated without --patches) there are no sets and every site runs the original.
//
// The patch page is the first 4 KiB page after main's image, inside the module window memory.c reserved: replacement
// code reaches it with one adrp, as MacNativeGames' data page after main (games/totk/runtime/game_patches.c). Its
// layout belongs to the sets that use it; a set that calls a host function registers it in rt_patch_hosts.
// Probe modes never call rt_patches_init: every set stays off.
#include "cfg.h"
#include "platform/platform.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "gamelib.h"
#include "host.h"

void rt_patches_init(void) {
    const RtGame *g = rt_game();
    if (!g->npatch_sets) return;
    if (!plat_mem_commit(g->patch_page, 0x1000))
        rt_fatal("patches: cannot commit the patch page at %#llx", (unsigned long long)g->patch_page);
    char list[512];
    size_t n = 0;
    list[0] = 0;
    for (int i = 0; i < g->npatch_sets; i++) {
        const RtPatchSet *s = &g->patch_sets[i];
        const char *e = cfg_get(s->env);
        // a set with a row in the settings table takes its default from there; the generated default serves the rest
        g->patch_on[i] = (uint8_t)(cfg_meta(s->env) ? cfg_bool(s->env) : e && *e ? strcmp(e, "0") != 0 : s->on);
        n += (size_t)snprintf(list + n, sizeof list - n, "%s%s %s", i ? ", " : "", s->name, g->patch_on[i] ? "on" : "off");
        if (n >= sizeof list) n = sizeof list - 1;
    }
    rt_log("patches: %s (page %#llx)", list, (unsigned long long)g->patch_page);
}

// The host entry points on the patch page, before the dispatch table is built (hostfn.c). No set of the game in use
// calls the host yet.
void rt_patch_hosts(void) {}

void rt_patch_switch(int set, int on) {
    const RtGame *g = rt_game();
    if (set >= 0 && set < g->npatch_sets) __atomic_store_n(&g->patch_on[set], (uint8_t)(on != 0), __ATOMIC_RELAXED);
}
