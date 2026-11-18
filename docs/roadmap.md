# Roadmap

What is being worked on, in order of priority: Orbitals playable from boot (no crash, a picture as on the console),
then nothing hanging the GPU, then the frame rate. Updated 17/11/2026 (branch `diag/frame-history-trace`; how the
work is done with a player's machine: [workflow.md](workflow.md)).

All measurements below are from one machine: Windows 11, RTX 4080, NVIDIA 616.92, Orbitals Deluxe Edition 1.0.5
(program `040032B023CA4000`, main build `d6efcc0a51c1c792`) with its add-on, from a `.nup` package. The reference is
the same dump on [Lichii](https://github.com/sinedgiveaways/Lichii-tool) (an Eden fork, used as a measuring tool only).

## Where the game is

- Boot, the three logos, the warning, the title, the main menu, the Deluxe add-on ("CONTENU BONUS DÉVERROUILLÉ",
  "GALERIE Deluxe"), the controller screen, the hero choice, the intro cutscenes and the start of the first level
  (split screen) run, with sound and both controllers, at 30 fps.
- Shaders: Orbitals' programs live in Unreal containers the setup does not read, so a run dumps every program it has
  no SPIR-V for into `<game>/spirv-dump` (default since `ffce7da`) and `tools/prepare/dumped_shaders.py` translates
  them. After a run into the first level: 687 programs dumped, 674 translated (98.1 %).

## 1. Open problems, most blocking first

### 1.1 The level's world draws black

Only the HUD, emissive glows and a few edges show in the first level; Lichii shows the colony lit.

- Measured: a frame dump of the level (`ORBITALS_DUMP=3900`, `images.txt`): the depth prepass is filled (geometry is
  placed), but the G-buffer passes write a base colour of 0 in R, G and B (alpha varies), normals of 0.5 everywhere and
  almost nothing in the other targets; the 8-target pass after them is all zero. The materials' pixel shaders run and
  output black.
- Ruled out: missing programs (674 of 687 translated, 14 still missing in that run), the graphics push constants the
  runtime drops (NVN2 keeps them in root table 0, read as constant bank 24, bank 17 after Eden's Ampere lowering:
  Lichii `src/video_core/engines/maxwell_3d.h`; `tools/shaders/c0_reads.py --banks` finds no Orbitals program reading
  bank 17 or 24, nor c0 below 0x110).
- Textures resolve (dump with `fd6ef01`), and since the handle tracking of `d1807eb` the G-buffer passes are right.
  `base_origin.py --keys` shows the handles come from two fixed c3 words OR'ed, with nothing in between.
- Since `d1807eb` translates it, pixel program `238181b409956cac` turns the whole level black again:
  `ORBITALS_SKIP_PROGRAMS=238181b409956cac` alone brings the characters back, skipping its near twin `9255edc18c6332c0`
  does not. `class_diff.py --keys 238181b409956cac,9255edc18c6332c0` finds no form unique to it.
- Suspect (unconfirmed): `.FMZ` on FMUL/FFMA (a zero factor gives 0, also against inf or NaN) was read as an IEEE
  multiply, so 0 × inf from an overflowing reciprocal gave NaN. The translator now emits `fmzmul` / `fmzfma`
  (encoding checked against nvdisasm: bit 76). **Next:** rerun `dumped_shaders.py`, run the level without
  `SKIP_PROGRAMS`. If still black, look at other NaN sources in that program (MUFU RCP/RSQ, FMUL scale), then compare
  its draw on Lichii.

### 1.2 A crash after the logos in about one run in three

`access violation ... reading address 0x104` in `f_7001759b20` (`main+0x1759b20`), Unreal's render graph popping an
element of an internal array (`main+0x1759d9c` loop, elements of 0xe8 and 0x40 bytes) and freeing its allocation
through `FMemory::Free` (`main+0xbf040`, a tail call to `GMalloc`'s vtable slot 0x50, which reads the thread's TLS).
The structure was corrupted earlier; the code reading it is right.

- Ruled out by A/B runs of 3-4 starts each: GPU write-backs (`ORBITALS_WB_MERGE=none`), asynchronous preemption
  (`ORBITALS_ASYNC_PREEMPT=0`), page freezing (`ORBITALS_FREEZE_IDLE=0`), the VRAM mirror (`ORBITALS_MEMORY=import`),
  and STLR ordered as a release store (fixed in `7b4a312`, a correct change, the crash stayed). The game library was
  checked rebuilt (its lifted code grew by 4 544 bytes).
- **Next:** the kernel's synchronization (`runtime/core/kernel/`: mutex arbitration, condition variables, events) for
  a path that lets two threads in at once; then the SDK functions the runtime replaces for threads and TLS.

### 1.3 Smaller visible differences

- The title and main menu backgrounds (nebula, starfield, menu art) are black, while their logos and text show.
- The "MAINTENIR (B) POUR PASSER" prompt is not drawn during cutscenes; holding B (Xbox B) does skip them.
- Logos 2 and 3 (Shapefarm, Kepler) are silent; on Lichii they have sound from about 10 to 18 s after start. Not
  investigated yet; the movie library (`nn::movie`, subsdk0) is initialized but no playback call shows in the logs.
- 13 programs are still refused by the translator: 5 `tex_scr_urc_` (handle in a uniform register not traced:
  `tools/shaders/base_origin.py --tex` shows where from), 3 `red__RaNonRZ` and 1 `atomg__RaNonRZ` (untraced global
  base), 2 `TLD4 2D AOFFI`, 2 shared-memory `ATOMS` forms.

## 2. Known trade-offs in the code

- Shader stores into storage buffers of unknown size (an address read from a uniform block) stay in the pool's VRAM
  mirror and are never copied to guest memory (`ORBITALS_WB_UNSIZED`, default `vram`): GPU work after them reads them,
  the CPU does not. Both ways back to guest memory failed (merged on the GPU: device lost; copied whole: corruption).
- Other shader stores go back merged by bytes on the CPU at the fence (`ORBITALS_WB_MERGE`, default 1). A merge in a
  compute shader lost the device inside its own dispatches four times; the cause was not found and that code is gone.
- Texel buffer views are cached (4096) and evicted least recently bound first.
- TXD's source order follows Ryujinx and is not checked against a picture yet (`sm86/translate/glsl/tex.py txd`).

## 3. Stability and memory

- Zero Vulkan validation errors (not measured on Orbitals yet; needs the Vulkan SDK on the player's machine).
- The NVN2 coverage: 171 procs listed and not implemented, 195 names without an implementation, out of 731 (from
  before the Orbitals runs; `tools/analisis/port_check.py`, `sdk_gaps.py`).

## 4. Frame rate

30 fps in the level with 2.6 GB a log interval compared by the merged write-back; no profile of Orbitals yet. The
replay thread's work found on the first game (recordings reused across frames, parallel recording) applies; its
numbers for Orbitals come from `tools/run/ab.py` runs (`ORBITALS_AB`).

## 5. The player's side

- Shaders are translated by hand after a run (`dumped_shaders.py`); the setup could do it at each start when
  `spirv-dump` grew.
- A Linux package that starts on non-rolling distributions, and the launcher tested on more Windows machines.
- Steam Remote Play Together checked with Orbitals ([remote-play.md](remote-play.md)).
