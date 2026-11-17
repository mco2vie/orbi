"""One text report on nn::vi::ListFrameHistory and the code that calls it, from the game's ExeFS.

Why: the frame-21 stall is a wait for ListFrameHistory entries (the game asks "how many" with out=0 count=0, then calls
again with count=1 and a buffer, main+0x1540460 and main+0x15404c0). Orbitals answers 0 and stores nothing because the
layout of nn::vi::FrameInfo is unknown. This report holds what is needed to read it: the symbols, the game's code after
the second call (which offsets of the buffer it reads) and the SDK's own ListFrameHistory (which offsets it writes). It is
built as a Windows executable by .github/workflows/frame-report.yml so it runs without git, uv or Python.

Usage: orbitals-frame-report.exe [EXEFS_DIR] [--out frame_report.txt] [--sym TEXT ...]
       uv run tools/analisis/frame_report.py [EXEFS_DIR] [--out frame_report.txt] [--sym TEXT ...]
--sym TEXT lists only the symbols whose name contains TEXT (full mangled names, every module, imports too):
no disassembly. Used to find the exact name of an SDK function to replace.
EXEFS_DIR holds main, sdk and subsdk0 (default: ORBITALS_GAME/exefs, ./exefs, or exefs next to the executable).
Builds the binary database in a temporary folder (about a minute), then writes the report. Nothing of the game is kept.
"""

import argparse
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # from the source tree; the frozen executable carries these modules itself
    _root = Path(__file__).resolve().parents[2]
    for _p in (_root / "recomp", _root / "tools/gpu", _root / "tools/analisis"):
        sys.path.insert(0, str(_p))
except IndexError:
    pass

import bindb  # noqa: E402
from capstone import CS_ARCH_ARM64, CS_MODE_ARM, Cs  # noqa: E402
from nso import Nso  # noqa: E402

CALLER_SITES = ("main+0x1540460", "main+0x15404c0")
CODE_WINDOW = ("main", 0x1540400, 0x1540700)  # module, start, end: around the Viewport thread's wait and both calls
FUNCTION_CAP = 400  # instructions printed for a whole function
NAMES = ("ListFrameHistory", "GetLatestFrameNumber")


def demangle_or_same(names: list[str]) -> dict[str, str]:
    """bindb's c++filt is not on Windows: keep the mangled names there (they still contain the readable words)."""
    try:
        res = subprocess.run(["c++filt"], input="\n".join(names), capture_output=True, text=True, check=True)
        return dict(zip(names, res.stdout.split("\n"), strict=False))
    except OSError, subprocess.CalledProcessError:
        return {n: n for n in names}


bindb.demangle = demangle_or_same


def find_exefs(arg: str | None) -> Path:
    cands = []
    if arg:
        cands.append(Path(arg))
    if os.environ.get("ORBITALS_GAME"):
        cands.append(Path(os.environ["ORBITALS_GAME"]) / "exefs")
    cands += [Path("exefs"), Path(sys.argv[0]).resolve().parent / "exefs"]
    for c in cands:
        if (c / "main").exists():
            return c
    sys.exit(
        "ExeFS not found (needs a folder with main, sdk and subsdk0). Pass it: orbitals-frame-report.exe C:\\path\\exefs"
    )


class Report:
    def __init__(self, db: sqlite3.Connection, exefs: Path) -> None:
        self.db = db
        self.exefs = exefs
        self.base = {m: b for m, b in db.execute("SELECT name, base FROM module")}
        self.names: dict[int, str] = {}
        for addr, name in db.execute("SELECT addr, name FROM plt WHERE name IS NOT NULL"):
            self.names[addr] = name
        for addr, name in db.execute("SELECT addr, name FROM func WHERE name IS NOT NULL AND name != ''"):
            self.names.setdefault(addr, name)
        self.images: dict[str, bytes] = {}
        self.md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
        self.lines: list[str] = []

    def out(self, text: str = "") -> None:
        print(text)
        self.lines.append(text)

    def rel(self, addr: int) -> str:
        for mod, base in self.base.items():
            if base <= addr < base + 0x10000000:
                return f"{mod}+{addr - base:#x}"
        return f"{addr:#x}"

    def image(self, mod: str) -> bytes:
        if mod not in self.images:
            self.images[mod] = bytes(Nso(str(self.exefs / mod)).image)
        return self.images[mod]

    def module_of(self, addr: int) -> str:
        return next(m for m, b in self.base.items() if b <= addr < b + 0x10000000)

    def disasm(self, lo: int, hi: int, cap: int | None = None) -> None:
        mod = self.module_of(lo)
        base = self.base[mod]
        rows = list(self.md.disasm(self.image(mod)[lo - base : hi - base], lo))
        if cap and len(rows) > cap:
            self.out(f"  (function has {len(rows)} instructions, first {cap} shown)")
            rows = rows[:cap]
        for i in rows:
            note = ""
            if i.mnemonic in ("bl", "b") and i.op_str.startswith("#"):
                t = int(i.op_str[1:], 16)
                note = f"  ; {self.rel(t)} {self.names.get(t, '')}"
            self.out(f"  {self.rel(i.address):>16}  {i.mnemonic:8} {i.op_str}{note}")

    def function_at(self, addr: int) -> tuple[int, int, str | None] | None:
        return self.db.execute(
            "SELECT addr, end, name FROM func WHERE addr<=? AND end>? ORDER BY addr DESC LIMIT 1", (addr, addr)
        ).fetchone()

    def symbols(self, patterns: list[str]) -> None:
        for pat in patterns:
            self.out(f"== Symbols containing {pat!r} (module, address, kind, name)")
            rows = self.db.execute(
                "SELECT module, addr, kind, name FROM sym WHERE name LIKE ? ORDER BY name, module", (f"%{pat}%",)
            ).fetchall()
            for mod, addr, kind, name in rows:
                where = self.rel(addr) if addr is not None else "(import)"
                self.out(f"  {mod:8} {where:20} {kind:7} {name}")
            if not rows:
                self.out("  (none)")
            self.out()

    def run(self) -> None:
        self.out("== Symbols (module, address, kind, name)")
        wanted = []
        for pat in NAMES:
            for mod, addr, kind, name in self.db.execute(
                "SELECT module, addr, kind, name FROM sym WHERE name LIKE ? ORDER BY module", (f"%{pat}%",)
            ):
                where = self.rel(addr) if addr is not None else "(import)"
                self.out(f"  {mod:8} {where:20} {kind:7} {name}")
                if addr is not None and kind == "func":
                    wanted.append((pat, addr, name))

        self.out("\n== The functions that contain the two ListFrameHistory calls")
        for site in CALLER_SITES:
            mod, off = site.split("+")
            addr = self.base[mod] + int(off, 16)
            f = self.function_at(addr)
            if not f:
                self.out(f"  {site}: no function found")
                continue
            callers = self.db.execute("SELECT caller FROM call WHERE target=? LIMIT 8", (f[0],)).fetchall()
            self.out(f"  {site}: function {self.rel(f[0])}..{self.rel(f[1])} ({(f[1] - f[0]) // 4} instructions)")
            self.out("     called from: " + (", ".join(self.rel(c[0]) for c in callers) or "(no direct caller)"))

        mod, lo, hi = CODE_WINDOW
        self.out(f"\n== The game's code {mod}+{lo:#x}..{hi:#x} (both calls, the wait at +0x1540434, what follows)")
        self.disasm(self.base[mod] + lo, self.base[mod] + hi)

        for pat, addr, name in wanted:
            f = self.function_at(addr)
            if not f:
                continue
            self.out(f"\n== The SDK's own {pat}: {name} at {self.rel(f[0])} ({(f[1] - f[0]) // 4} instructions)")
            self.disasm(f[0], f[1], FUNCTION_CAP)
        if not wanted:
            self.out("\n(no ListFrameHistory/GetLatestFrameNumber function symbol with an address: only imports)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("exefs", nargs="?")
    ap.add_argument("--out", type=Path, default=Path("frame_report.txt"))
    ap.add_argument("--sym", action="append", default=[], help="list the symbols whose name contains this text")
    args = ap.parse_args()
    exefs = find_exefs(args.exefs)
    print(f"ExeFS: {exefs.resolve()}\nBuilding the binary database (about a minute)...")
    # The database file stays open under Windows until the process ends, so the temporary folder cannot always be removed.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        dbpath = Path(tmp) / "bindb.sqlite"
        bindb.build(exefs, dbpath)
        db = sqlite3.connect(dbpath)
        rep = Report(db, exefs)
        print("\n----- report -----")
        if args.sym:
            rep.symbols(args.sym)
        else:
            rep.run()
        args.out.write_text("\n".join(rep.lines) + "\n", encoding="utf-8")
        db.close()
    print(f"\nReport written to {args.out.resolve()} ({len(rep.lines)} lines)")


if __name__ == "__main__":
    try:
        main()
    finally:
        if len(sys.argv) == 1 and getattr(sys, "frozen", False):
            input("Press Enter to close")
