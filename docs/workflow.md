# Working on Orbitals with a player's machine

How the work of November 2026 was done, for whoever takes it over: the game, its dump and the GPU are on a player's
Windows PC; the code, the builds and the analysis are elsewhere. What is open is in [roadmap.md](roadmap.md).

## Repositories and branches

| Repository | Branch | What it is |
|---|---|---|
| `sinedgiveaways/pmocer-latibro` | `orbitals-port` (default), `diag/frame-history-trace` (the work since 16/11/2026) | The static recompilation: `recomp/` lifts AArch64 to C, `runtime/` replaces the SDK and NVN2 (over Vulkan), `sm86/` translates shaders to SPIR-V |
| `sinedgiveaways/Lichii-tool` | `analysis/recomp-build` | An Eden fork used as a measuring tool: it runs the real SDK and NVN2 driver; its GDB stub, `lichii-probe.exe`, its GPU traces (`docs/nx2/gpu-trace.md`) and its code say what the console does |

The recompilation never emulates the CPU or the GPU. Lichii is only a reference to measure against.

## Builds

- `gh api -X POST repos/sinedgiveaways/pmocer-latibro/actions/workflows/build-windows.yml/dispatches -f ref=<branch>`
  starts the Windows build; a push alone does not. The artifact is `orbitals-recomp-windows-x64`.
- The player copies it over their `orbitals-recomp` folder, keeping `spirv/`, `spirv-dump/` and `aoc/`.
- The game code (`orbitalgame.dll`) is generated and compiled on the player's machine by the setup. Its key is
  `recomp/*.py`, `runtime/cpu/*.h`, `tools/build/build.py` and `tools/prepare/gamecode.py`
  (`tools/prepare/prepare.py` `COMPILER`): a change there recompiles the game at the next start (minutes), a change
  elsewhere in `runtime/` only needs the new executable. To check a recompile took place: the log's
  `lifted code exe+...-exe+...` range changes size.
- The shader translator (`sm86/`, `tools/shaders/`) runs from `setup/src` with the package's own Python. A change
  there can reach the player without a build:
  `Invoke-WebRequest https://raw.githubusercontent.com/sinedgiveaways/pmocer-latibro/<commit>/<path> -OutFile setup/src/<path>`,
  pinned to a commit (the branch URL can serve a cached older file for minutes).

## Commands on the player's side

From the `orbitals-recomp` folder, in PowerShell. Paths use forward slashes: a `\n` in a pasted path (as in
`prepare\nup.py`) becomes a line break, which cut every early attempt of these commands in two.

| Command | What it does |
|---|---|
| `.\setup\python\python.exe setup/src/tools/prepare/nup.py addons "<game>.nup" .` | Unpacks the add-ons (the Deluxe content) into `aoc/<index>/`; the setup's romfs step does it too |
| `.\setup\python\python.exe setup/src/tools/prepare/dumped_shaders.py --dumped spirv-dump` | Translates every dumped program into `spirv/`; prints the valid count and the refusal reasons (`spirv/failed.tsv`) |
| `.\setup\python\python.exe setup/src/tools/shaders/base_origin.py --dumped spirv-dump [--tex]` | Counts where the untraced storage buffer bases (or, `--tex`, texture handles) of the refused programs come from |
| `.\setup\python\python.exe setup/src/tools/shaders/c0_reads.py --dumped spirv-dump [--banks]` | Counts which constant bank words the programs read at fixed addresses, by stage |
| `.\setup\python\python.exe disasm_fn.py exefs main+0x<offset> --count N` | Disassembles game code at a crash address (`Lichii-tool/tools/nx2/recomp/disasm_fn.py`); its output only goes into a chat, never into a file in a repository |

A run that meets new programs dumps them; translating them and running again is the loop that brought the level from
211 to 687 programs. Each pass can reveal more.

## Exchanging data

The player uploads `.7z` archives to the `analysis-data` release of `Lichii-tool`; each asset is downloaded with
`gh api -H "Accept: application/octet-stream" repos/sinedgiveaways/Lichii-tool/releases/assets/<id>` (`gh release
download` fails in some environments) and deleted right after (`gh api -X DELETE .../releases/assets/<id>`).

Nothing derived from the game goes into a repository or stays on a release:

| May be uploaded | Must not be uploaded |
|---|---|
| `orbitals.log`, `spirv/failed.tsv`, the census outputs above, a frame dump's `images.txt`, `passes.txt`, `stats.txt`, screen recordings | `spirv-dump/`, `spirv/*.spv`, a dump's `.png` and `sh_*.spv`, `exefs/`, the RomFS, Lichii GPU traces (`.lxtrace`), disassembly |

A recording is read by extracting frames and the audio level per second with ffmpeg (a contact sheet every few
seconds; `astats` RMS per second to tell a silent logo from a quiet one).

## Diagnosing

- **Log lines worth reading first:** `FATAL`, `device fault`, the GPU breadcrumbs (the hang lies after the last
  finished mark and up to the last started one), `gfx_shader: N programs without SPIR-V dumped`, `no prepared SPIR-V`,
  `write-backs merged by bytes since the last line`, `texel buffer views: the table was full`. Filter the noise with
  `Select-String -NotMatch` on `AllocateMemoryPages`, `sdk call`, `fs entry`, `nn::codec: queued`.
- **A frame dump:** `DUMP = <frame>` in `orbitals.ini` writes `dump/` (one PNG per pass, `images.txt` with each
  target's min and max, `passes.txt` with every pipeline, its shaders and bindings). `images.txt` alone says at which
  pass a picture goes black. The frame number is counted from boot; the log's `frametime: exit` and `replay queue over
  the run to frame N` lines say where a scene was.
- **A/B runs:** one setting changed, 3 to 4 starts each, the crash count compared. A crash that happens one start in
  three needs at least that many to rule a cause out.
- **A crash in game code:** the report gives the lifted function, `pc`, `lr` and the guest frames; `disasm_fn.py` on
  the player's exefs shows the code around them.
- **Lichii first** when the question is what the console does: the probe for SDK call arguments and results, its code
  for the NVN2 driver's behavior (root tables, push constants), a GPU trace for a whole frame.

Settings used to bisect (all in [environment-variables.md](environment-variables.md)):

| Setting | Values |
|---|---|
| `WB_MERGE` | 1 (default) shader stores merged back by bytes on the CPU; 0 copied back whole; `none` not copied back |
| `WB_UNSIZED` | `vram` (default), `merge`, `whole`: stores into storage buffers of unknown size |
| `TEXEL_VIEWS` | 1 (default); `read` storage texel buffers bind the zero view; 0 every texel buffer does |
| `SPIRV_DUMP` | where programs without SPIR-V are dumped (default `<game>/spirv-dump`); 0 none |
| `ASYNC_PREEMPT`, `FREEZE_IDLE`, `MEMORY` | 0 / 0 / `import`: preemption, page freezing, the VRAM mirror off |
| `PUSH_CS`, `VATTR_MAX` | 0: compute push constants dropped; 16-32: vertex attributes kept |
| `GPU_CRUMBS`, `SKIP_PROGRAMS`, `VK_VALIDATION` | breadcrumbs off; draws with listed programs skipped; the validation layer (needs the Vulkan SDK) |

## Checking a change without the game

- `PYTHONPATH=<cogapp> python3 tools/docs/check.py` (every folder's README, every file listed) before each commit.
- A C syntax check: `clang -std=gnu11 -fsyntax-only` over the changed file with every `runtime/` folder on the
  include path, the Vulkan headers, VMA and SDL3; `simd_fp.h`'s 27 errors are known and unrelated.
- Shaders of the runtime: `glslc --target-env=vulkan1.2` and `spirv-val`, then `tools/shaders/embed_spv.py`.
- The translator needs Python 3.14 (`compression.zstd`) and the SM86 spec, which `python sm86/spec/spec.py --out
  build/sm86 --cc clang` builds from NVIDIA's redistributable nvdisasm and ptxas (a download, about a minute).
- Real SASS for a test: assemble a small PTX with that ptxas (`-arch=sm_86`), take `.text.<kernel>` from the cubin
  and decode it with `sm86/translate/program.py`; flipping single bits of a decoded word finds the encoding of another
  instruction class (an `ldg_uniform__Ra32`, a ULDC of bank 3) when ptxas never emits it. The translated GLSL then goes
  through glslc.
