# pmocer-latibro

A static recompilation project for orbital built around a custom runtime and shader translation pipeline.

This repository aims to recreate the game's behavior on x86-64 by recompiling the Switch 2 AArch64 code into C, replacing the console runtime with a native implementation, and translating SM86 shaders into SPIR-V for Vulkan-backed execution.

## What this project contains

- `recomp/` — translated game code and recompilation infrastructure
- `runtime/` — runtime implementation replacing the console's kernel and SDK behavior
- `sm86/` — SM86 shader translation and GPU-related tooling
- `tools/` — build, test, diagnostics, and documentation utilities
- `tests/` — validation and regression tests
- `docs/` — project documentation, roadmap, research notes, and release information
- `i18n/` — in-game text translations

## Project goals

- Recompile the game without CPU emulation or JIT execution
- Reimplement the runtime at the API level instead of emulating console services
- Keep the runtime faithful to console defaults and behavior
- Validate fixes with targeted tests, captures, and probes before wider game runs

## Getting started

This project uses Python tooling via `uv`.

```bash
uv sync
uv run tools/analisis/bindb.py
```

For repository conventions and development guidelines, see:

- `AGENTS.md`
- `CONTRIBUTING.md`
- `docs/roadmap.md`

## Documentation

- `docs/README.md` — documentation index
- `docs/roadmap.md` — current work and priority items
- `docs/research.md` — source and research notes
- `i18n/README.md` — translation workflow and text catalogs

## Rules and expectations

The project follows strict rules for correctness and compatibility:

- no CPU interpreter or JIT
- no GPU emulation below NVN2
- no game assets or generated game code checked into git
- source code must comply with licensing and attribution rules
- fixes should be implemented at the source of the bug, not disabled globally
- tests and measurements should be run before and after relevant changes

## Status

This repository is a work in progress. See the roadmap and development notes for the current implementation priorities.
