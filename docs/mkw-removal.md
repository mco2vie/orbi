# MKW removal

What of the first game (Mario Kart World) and of the project this one is forked from (mkw-recomp) was removed from
the product, what was kept and why, and the proof from the built executable. Filled commit by commit on the branch
`cleanup/mkw-removal`; the plan is [mkw-removal-plan.md](mkw-removal-plan.md) and the starting inventory
[mkw-inventory.tsv](mkw-inventory.tsv). Completed and checked at the end of the removal (the plan's last commit).

## Removed from the product

| What | Commit | Why |
|---|---|---|
| The game's own text tables `i18n/game/*.tsv` | `a970f7d` | Text of the first game; game content does not go in the repository |
| MKW's rows in `recomp/versions.py` and `runtime/core/boot/version.c`, `recomp/patches-mkw*.txt` | `9952d83` | Addresses and patch sites of MKW builds; Orbitals has its own row |
| Patch sets shadow, seed, aspect, output, camera, frame rate; `ov_zstd.c` | `9952d83` | Hooks on MKW functions and classes |
| `MKW_*` names: every setting is `ORBITALS_*`, no alias | `3c30c42` | Product name; `tools/migrate_config.py` moves old settings once |
| The settings FPS, aspect, shadow size | `3c30c42` | No effect without the MKW patch sets |
| Artifact names: `mkw.exe`, `libmkw.dll.a`, `mkw.def`, `mkw.rc`, linker sections, `orbital.ini`, logs, Linux data folder | `285e3cf` | Product name `orbitals-recomp` |
| `romfs_res.c`, the settings Resolution and Detail distance, `tools/romfs/resolution.py` | `b2ed262` | Reads a RomFS file Orbitals does not have ([romfs-res-audit.md](romfs-res-audit.md)) |
| Links to `adriadam10/mkw-recomp`, the `mkw-recomp:` link scheme | `09ea19e` | The project's repository is `sinedgiveaways/pmocer-latibro` |
| Known-issues signatures list (`tools/github/signatures.toml`) | this commit | Known-issues signatures list emptied: the MKW entries referenced issues from the original repo. Orbitals-specific signatures will be added as errors are discovered |

## Kept, with the reason

| What | Why |
|---|---|
| `LICENSE` (MIT, the original author's copyright) and the copyright lines in file headers | The MIT licence requires the notice to stay in copies |
| `recomp/LICENSE.totk-pc-recomp`, `runtime/LICENSE.totk-pc-recomp` | Same, for totk-pc-recomp |
| Third-party sources named in comments: `seedds/mkw-neo`, MacNativeGames' `mkw_vpool.c`, `mkw_xlate` and `mkw_nvn_ext.c`, MKW-THWOMP | Attribution of where code or ideas came from; comments, not in the executable |
| `tools/migrate_config.py`, `tools/migrate/mkw-to-orbitals.tsv`, `docs/environment-variables.md`'s former names | One-shot migration and its reference; never loaded by the runtime |
| `docs/performance.md`'s table of MKW reports | Historical measurements with links to the reports in the original repository; to be replaced |

## Proof in the executable

To be written at the end: the counts the Windows build prints (`.github/workflows/build-windows.yml`, step "Old names
in the executable"), UTF-8 and UTF-16.
