# Roadmap

What is being worked on, in order of priority: Orbitals running from boot to play, then nothing hanging the GPU, then
the picture as on the console, then the frame rate. Updated 16/11/2026, after the removal of the first game's code
([mkw-removal.md](mkw-removal.md)).

## 1. Orbitals from boot to play

The setup recognises Orbitals (`recomp/versions.py`, version 1) and the runtime has a row for it
(`runtime/core/boot/version.c`) with no guest address measured yet: every feature that needs one is off and says so in
the log.

- Boot constants from a run with logs on: the return address of the first `nvnBootstrapLoader` call and each module's
  `DT_INIT` count (`version.c` says which log lines give them), the NVN2 device table of Orbitals' own sdk
  (`tools/gpu/gen_nvn2_devinfo.py`), its display version (`nn::oe::GetDisplayVersion` answers "unknown").
- The main thread with the priority, core and stack `main.npdm` asks for (`kernel.c` builds fixed values; `boot.c`
  logs the difference).
- SDK coverage: 991 of Orbitals' 1 305 SDK imports are not replaced yet, 319 of them backed by a console service
  (`tools/analisis/port_check.py`, `sdk_gaps.py`).
- NVN2 coverage: 171 procs listed and not implemented, 195 names without an implementation, out of 731.
- First run of the game (16/11/2026, RTX 4080, Windows): the SDK and the 1 990 `DT_INIT` constructors run, `nnMain`
  is reached, Unreal reads its pak and config files, the audio and NVN start, frames are presented. At 120 s Unreal's
  watchdog (`GameThread timed out waiting for RenderThread`) aborts the run through `svc #0x26 Break`. In the dump
  every thread is waiting on an event and none is running, so it is a missing signal, not a loop. The log also shows
  `no prepared SPIR-V` and draws skipped for it. Whether the two are linked is **not known**; no run of the first
  game exists as a baseline for Orbitals. The way forward, in this order:
  1. **Which event is never signalled.** Read the log with `shader_analyzer.exe` ([log-analyzer.md](log-analyzer.md)) to
     drop the allocation noise and count the presents, then find the fence, vsync or
     frame-history wait the RenderThread and the Viewport thread sit on (`main+0x4a6d4`, `main+0x1540434`).
     `nn::vi::ListFrameHistory` answers 0 today. A second run with draws without a shader made non-blocking would
     tell whether the shaders are the cause; no such switch exists yet (`ORBITALS_PIPE_SKIP` is about draws whose
     pipeline is still building).
  2. **Fix what step 1 finds.** Shader work only if step 1 points at it.
  3. **Shaders.** Where Orbitals' programs are (its RomFS is Unreal `.pak`/`.utoc` containers, no BNSH archive) and
     how they reach NVN2; the log's `no prepared SPIR-V <hash>` lines are the hashes of the blobs the game hands to
     `nvnProgramSetShaders`, which may be captured at run time (to check). The setup's shader step is skipped for
     Orbitals (`skip_steps`) until then. The image atomic with its handle in a register (Ampere instruction 394) is
     a known blocker of the translator for this game.
- The save format, if hacks on the save are wanted again (the former one was the first game's).

## 2. Stability and memory

- GPU hangs on AMD: upload batches already split; next, breadcrumbs and `VK_EXT_device_fault` to find the cause of the
  remaining ones.
- Five kernel and platform bugs inherited from totk-pc-recomp (the fiber stack alignment can crash a run).
- Zero Vulkan validation errors.

## 3. The picture as on the console

- Push constants of constant bank 24 are not passed yet.
- Task/mesh shaders as compute.
- A lower render resolution on weak GPUs (the Steam Deck), through Orbitals' own engine settings: the former setting
  wrote the first game's RomFS parameters ([romfs-res-audit.md](romfs-res-audit.md)).

## 4. Frame rate: the replay thread

Measured in the first game's races (07-09/11/2026, Radeon 660M, Linux, 720p): a frame took 31-33 ms, of which the
Vulkan back end recording the game's big submit on the replay thread took ~19 ms, on the critical path. The back end
is the same for Orbitals; its own numbers come from `tools/run/ab.py` runs (`ORBITALS_AB`) once it reaches a scene.
Already done: recordings reused across frames, recording overlapped with the game, submits on their own thread, the
shadow copies off the replay thread, the replay thread on its own core. Next:

- Dynamic state recorded only when it changes (idea and code from totk-pc-recomp, MIT).
- Less work per draw: descriptor sets kept across frames by their contents (`ORBITALS_DRAW_CACHE`).
- Recording in parallel: chunks of a submit on several threads; they fight over the texture lock, which has to be
  split first.
- The kernel's global lock: waits by address are done; the rest of the lock remains.
- The game thread: the generated C at `-O1`, with profile-guided optimization next.

## 5. The player's side

- A Linux package that starts on non-rolling distributions (glibc 2.31 through zig), and the launcher tested on real
  Windows machines.
- Windows with a dedicated GPU: memory the GPU wrote is not uploaded again to its mirror.
- "Detect" in the graphics settings: a preset picked from the GPU.
- Steam Remote Play Together checked with Orbitals ([remote-play.md](remote-play.md)).
- Translations of the README and of the two texts that changed (the missing-game help and the wrong-build error).
