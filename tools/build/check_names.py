"""Scan a folder, a file or a built executable for names of the project this one descends from.

Why: the product (sources, docs, packages, executables) must not carry the old game's or project's name. A text search
on a binary misses UTF-16 strings (Windows version resources, manifests), so every file is read as bytes and searched
both as UTF-8 and as UTF-16LE.

Names looked for (case-insensitive): MKW, MarioKart, Mario Kart, MKWorld, mkw-recomp, adriadam10. In a binary the
three-letter "mkw" counts only when no letter touches it, to avoid hits inside compressed data.

Paths listed in the allow file (default tools/build/check_names.allow, globs relative to the scanned root) may keep the
names: the licence texts, the third-party notices, the removal report and the one-shot migration data.

Usage: uv run tools/build/check_names.py PATH [PATH ...] [--allow FILE] [--limit N] [--strict]
       Report only by default; --strict exits 1 when something outside the allow file matches.
"""

import argparse
import fnmatch
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}

# What a file name may not contain.
NAMES = ("mario kart", "mariokart", "mkworld", "mkw-recomp", "mkw_recomp", "adriadam10")
TEXT_RE = re.compile("|".join(re.escape(n) for n in NAMES) + "|mkw", re.I)


def variants(binary: bool) -> list[re.Pattern]:
    """Byte patterns: UTF-8 and UTF-16LE spellings of every name."""
    out = []
    plain = list(NAMES) + (["libmkw"] if binary else [])
    for n in plain:
        out.append(re.compile(re.escape(n.encode()), re.I))
        out.append(re.compile(re.escape(n.encode("utf-16le")), re.I))
    mkw8 = rb"(?<![A-Za-z])mkw(?![A-Za-z])" if binary else rb"mkw"
    mkw16 = (rb"(?<![A-Za-z]\x00)m\x00k\x00w\x00(?![A-Za-z]\x00)" if binary else rb"m\x00k\x00w\x00")
    out.append(re.compile(mkw8, re.I))
    out.append(re.compile(mkw16, re.I))
    return out


def load_allow(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    lines = [l.strip() for l in path.read_text().splitlines()]
    return [l for l in lines if l and not l.startswith("#")]


def allowed(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(rel, p) or fnmatch.fnmatchcase(Path(rel).name, p) for p in patterns)


def files_of(root: Path):
    if root.is_file():
        yield root, root.name
        return
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.is_file() and not p.is_symlink():
            yield p, p.relative_to(root).as_posix()


def scan(path: Path) -> list[tuple[str, str]]:
    """(kind, snippet) of every match in the file."""
    data = path.read_bytes()
    binary = b"\x00" in data[:8192] and not data[:2] in (b"\xff\xfe", b"\xfe\xff")
    hits = []
    for rx in variants(binary):
        for m in rx.finditer(data):
            a = max(0, m.start() - 20)
            snip = data[a : m.end() + 20]
            snip = snip.decode("utf-16le", "replace") if b"\x00" in m.group(0) else snip.decode("utf-8", "replace")
            hits.append(("utf-16" if b"\x00" in m.group(0) else "utf-8", " ".join(snip.split())))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--allow", type=Path, default=HERE / "check_names.allow")
    ap.add_argument("--limit", type=int, default=3, help="snippets shown per file")
    ap.add_argument("--strict", action="store_true", help="exit 1 when a file outside the allow file matches")
    args = ap.parse_args()
    patterns = load_allow(args.allow)

    bad = kept = 0
    for root in args.paths:
        if not root.exists():
            print(f"check_names: {root} does not exist", file=sys.stderr)
            return 2
        # Filenames are checked too.
        for p, rel in files_of(root):
            ok = allowed(rel, patterns)
            hits = scan(p)
            if TEXT_RE.search(rel):
                hits.insert(0, ("filename", rel))
            if not hits:
                continue
            if ok:
                kept += len(hits)
                continue
            bad += len(hits)
            print(f"{rel}: {len(hits)} match(es)")
            for kind, snip in hits[: args.limit]:
                print(f"    [{kind}] {snip[:110]}")
    print(f"check_names: {bad} match(es) outside the allow file, {kept} inside it")
    return 1 if (bad and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
