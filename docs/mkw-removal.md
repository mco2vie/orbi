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
| Known-issues signatures list (`tools/github/signatures.toml`) | `d4ee6d3` | Known-issues signatures list emptied: the MKW entries referenced issues from the original repo. Orbitals-specific signatures will be added as errors are discovered |
| Texts naming the first game, and the texts of removed settings, in `i18n/` | `1b5e55e` | The missing-game help and wrong-build error name Orbitals; 13 ids of removed settings dropped from the 21 catalogs |
| Unlock everything (`runtime/core/hacks/unlock.c`, `unlock_ids.c`, `ORBITALS_UNLOCK_ALL`) | `5dde6e8` | See "unlock.c audit" below |
| The Mods page's GameBanana tab (`mods_browse.cpp`, `tools/mod/gamebanana.py`, `--gb-install`, the `orbitals-recomp:` link handler, `plat_url_scheme`, `stb_image.h` used only for its previews, 17 texts) | this commit | GameBanana mods tab removed: it listed Mario Kart World mods (game ID 22152). Orbitals has no GameBanana presence. The mods page now only shows local mods |
| Quick Race (`ORBITALS_QUICK_RACE`, its menu row, 4 texts, the press scripts in `input_script.c`) | this commit | Quick Race removed: it navigated MKW's menus (time trial, Mario, standard kart). Orbitals has no equivalent menu structure |

## Kept, with the reason

| What | Why |
|---|---|
| `LICENSE` (MIT, the original author's copyright) and the copyright lines in file headers | The MIT licence requires the notice to stay in copies |
| `recomp/LICENSE.totk-pc-recomp`, `runtime/LICENSE.totk-pc-recomp` | Same, for totk-pc-recomp |
| Third-party sources named in comments: `seedds/mkw-neo`, MacNativeGames' `mkw_vpool.c`, `mkw_xlate` and `mkw_nvn_ext.c`, MKW-THWOMP | Attribution of where code or ideas came from; comments, not in the executable |
| `tools/migrate_config.py`, `tools/migrate/mkw-to-orbitals.tsv`, `docs/environment-variables.md`'s former names | One-shot migration and its reference; never loaded by the runtime |
| `docs/performance.md`'s table of MKW reports | Historical measurements with links to the reports in the original repository; to be replaced |

## unlock.c audit

`unlock.c` edited the save when the game opened `Play/account.sav`: it added every driver, vehicle and sticker id to
the owned lists, revealed the Special Cup and opened Mirror. Everything in it is the first game's: the file name, the
save's magic and key hashes, a fallback to that game's 1.0.0 offsets, and 1 100 item ids taken from Ca1nM's Mario Kart
World save editor (MIT). For any other save it logged "not a layout this knows" and changed nothing, so for Orbitals the
Hacks tab's "Unlock everything" row did nothing. Removed with its setting, menu row and texts; an Orbitals equivalent
would need its own save format, found from its saves.

## Proof in the executable

To be written at the end: the counts the Windows build prints (`.github/workflows/build-windows.yml`, step "Old names
in the executable"), UTF-8 and UTF-16.
