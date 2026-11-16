# Steam Remote Play Together: status

16/11/2026, branch `cleanup/mkw-removal`. Read from the code and the build logs; nothing here was run with Orbitals.

## Verdict: partial

The feature is **implemented in full and builds**, and it is the same code that shipped in the earlier project's
release `v0.1.11-rpt8`. It was checked against a mock of Steam, never in a real session, and **not run with Orbitals**.
What decides whether it is useful there (does Orbitals offer local multiplayer, through which SDK calls) is not known
yet.

| | State |
|---|---|
| Steam API start, callbacks, sessions, overlay invite, guest link | Implemented |
| Guests' controllers as players, guests' keyboards as players | Implemented (generic: SDL gamepads and Steam direct input) |
| The "local players or Remote Play Together" choice when controllers are missing | Implemented, hooked on `nn::hid::ShowControllerSupport`; whether Orbitals calls it is unknown |
| Settings, menu rows, texts, guide (`docs/remote-play.md`) | Present, named `ORBITALS_STEAM_*` |
| Steam's library in the Windows package | **Missing**: not in the zip, only fetched by a `uv` script |
| Tests | **None** for this code (`tests/` has no Steam test; CI only compiles it) |
| Run against a real Steam, with the first game or with Orbitals | **Not done** (a mock only, 13/11/2026) |

## Evidence

- **Same implementation as `v0.1.11-rpt8`.** The release `v0.1.11-rpt8` of `sinedgiveaways/mkw-recomp` (MIT, 14/11/2026)
  has `runtime/steam/{steam_rpt.c, steam_rpt.h, steam_flat.h}`. After mapping the names back (`ORBITALS_` to `MKW_`,
  `orbitals-recomp` to `mkw`, `orbitals.ini` to `mkw.ini`), the three files here have **0 differing lines** (488, 58
  and 121 lines). So the rename changed no behaviour, and the plan "follow rpt8" is already what the tree holds. The
  release's notes mention Steam only for the Steam Deck. The guide's own "Tested" section (`docs/remote-play.md`, 13/11/2026)
  says what was run: Valve's SDK 1.65 library and a mock of Steam built from Valve's headers, SDL virtual gamepads
  standing in for the guests' controllers, and "a real session with friends over Steam has not been run yet". The mock is
  not in the repository. So even for the first game this was checked against a mock, never against a live Steam.
- **Calls to Steam** (`steam_flat.h:97-113`, bound by name at run time, `steam_rpt.c:417` `steam_rpt_start`):
  `SteamInternal_SteamAPI_Init`, manual callback dispatch (`ManualDispatch_*`), `ISteamRemotePlay::GetSessionCount`,
  `GetSessionID`, `GetSessionSteamID`, `GetSessionClientName`, `ShowRemotePlayTogetherUI`,
  `BSendRemotePlayTogetherInvite` (guest link), `BEnableRemotePlayTogetherDirectInput`, `GetInput`,
  `SetMouseVisibility`; `ISteamFriends::GetFriendPersonaName`. Interfaces `SteamFriends018` and
  `STEAMREMOTEPLAY_INTERFACE_VERSION004` (SDK 1.62 or newer).
- **Callbacks.** `SteamAPI_RunCallbacks` is replaced by manual dispatch on a dedicated `steam` thread every 8 ms
  (`steam_rpt.c:360` `steam_main`, `:290` `callbacks`), so no Steam code runs on a game thread. Sessions are also read
  again once a second (`:269` `sync_sessions`).
- **Start order.** `main.c:654` calls `steam_rpt_start()` before `rt_boot()`, so the overlay can hook the Vulkan device
  and SDL sees Steam's virtual gamepads (`steam_rpt.c:482`, `SDL_GAMECONTROLLER_ALLOW_STEAM_VIRTUAL_GAMEPAD`). It saves
  and gives back the signal handlers Steam replaces (`plat_handlers_save`).
- **Guests as players.** Controllers: `input.c:162` `steam_virtual`, `:240` joins them as the next free player (2-8).
  Keyboards: `steam_rpt.c:313` `read_keys` and `input.c:574` `input_remote_attach`, on the host's key table, only for a
  guest without a controller and after the guest's first 5 s.
- **The choice.** `ov_input.c:204` `ov_controller_support` calls `steam_rpt_multiplayer(lo, have)` (`steam_rpt.c:183`):
  with fewer controllers than players, a menu asks "local players" or "Remote Play Together" and the second opens the
  invite list (`steam_invite` = ask, auto, always, off).
- **Menu.** `settings_tabs.cpp:237` onward, the group "Remote Play Together": App ID (off, automatic, RetroArch 1118310,
  typed ones), Invite friends, Copy guest link.
- **Build.** The Windows build of pull request #2 compiles these files with no warning of their own.

## What is missing or unknown

1. **No run with Orbitals.** It does not reach a scene yet ([roadmap.md](roadmap.md)), so none of the above is
   observed on it: not the overlay, not a guest joining, not a controller becoming player 2.
2. **Does Orbitals ask for local multiplayer, and how?** The choice menu only appears if Orbitals calls
   `nn::hid::ShowControllerSupport` with at least 2 players (`ov_input.c:575`). Without it, the Invite and Copy-link
   buttons and the guests' controllers still work if Orbitals reads several npad ids, but nothing opens the invite
   list by itself. Check in `port_check.md` (PowerShell, from the folder holding it):
   `Select-String -Path port_check.md -Pattern 'ShowControllerSupport|SetSupportedNpadIdType|GetNpadStates|SetNpadJoyAssignment'`.
   The result says which `nn::hid` calls Orbitals imports.
3. **Player count.** The runtime allows 8 (`INPUT_MAX_PLAYERS`, `input.h:16`) and the guide says "up to 8". That was
   the first game's split-screen limit; Orbitals' own limit is not known. The comment at `ov_input.c:203` still names
   that game's address (`main+0x25da6c8`) for the applet argument; Orbitals' layout of that argument is unchecked.
4. **The App ID is borrowed, not Orbitals'.** Steam only offers Remote Play Together for an App ID that is in the
   host's library and has the feature on. This project is not a Steam app, so the runtime starts the Steam API as an
   App ID the host already owns (RetroArch, 1118310, is the documented one) and Steam shows that game's name to the
   guests. A Steamworks application of its own (a partner account and a store page) would be the clean route; it is not
   something this repository can set up. The guide says so ("Use an App ID you own or are allowed to use"). Whether
   to keep this approach is a decision for you.
5. **Steam's library is not in the package.** `release.py` and `dist.py` do not copy `steam_api64.dll` or
   `libsteam_api.so`; `tools/build/steamlib.py` downloads them (SDK 1.65 from the Steamworks.NET release, checked by
   sha256) and the guide tells the player to run it with `uv`, which a Windows player with the zip does not have.
   Valve's redistribution terms for that file (the Steamworks SDK Access Agreement) are not something I can judge:
   please read them before shipping it. Meanwhile the player has to put the library next to the exe by hand.
6. **No automated test.** Pure logic exists that could be tested without Steam: `steam_rpt_saved_ids` and
   `steam_rpt_saved_add` (the typed App IDs list), `is_app_id`, and the choice of `steam_rpt_multiplayer` by mode.
   The Steam calls themselves need a Steam client.
7. **Linux only paths.** Flatpak and Snap Steam cannot work (the guide says so); the AppImage's data folder for
   the library is `~/.local/share/orbitals-recomp`, now correct after the rename.

## Plan

Following the shape of `v0.1.11-rpt8` (which this tree already is), what is left is validation and packaging, in order:

1. **Find what Orbitals imports** (item 2 above, one `Select-String`), and note it in this page. If it imports
   `ShowControllerSupport`, the automatic choice works as designed. If not, list the npad calls it uses and add the
   override for the one that asks for several players (no change to `steam_rpt.c`).
2. **A first run against a real Steam**, the check nobody has made: when Orbitals reaches a scene, with `steam_appid = 1118310` (or another owned App ID), Steam running and the
   library next to the exe. Look for the log lines `steam: running as App ID ...; Remote Play Together ready`, then
   `steam: ... joined (session ...)`, then `input: gamepad ... for player 2 (... a Remote Play guest's)`. The guide lists them under "Set up". Risk: unknown: the code has only met a mock of Steam, and Orbitals has to offer a scene with several players.
3. **Package the library** once the redistribution question is settled: `steamlib.py` called by `dist.py` for the
   target, the file added to the zip and the AppImage, and the guide updated. Risk: legal, not technical.
4. **Add the tests of item 6** as a C probe built the way `tests/c/` builds its probes, plus a CI step. Estimated: a
   few hours; no gameplay risk.
5. **Orbitals' own limit of players** (item 3), from its first multiplayer scene, in `input.h` and the guide.

Not planned: a Steamworks application for Orbitals, and any code from Eglantine's Remote Play extension (GPL-3.0; the
idea was the only thing taken, as `runtime/steam/README.md` says).
