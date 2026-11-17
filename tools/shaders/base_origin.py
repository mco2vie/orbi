"""Where the uniform base of the global accesses comes from, in the dumped programs the translator refuses with
"base not a traced storage buffer" (LDG/STG/ATOMG [Ra + URb]): for each such access, the instructions that last wrote
its base register before it, walked back a few steps, counted by shape (mnemonic, class and constant bank operands, no
other bits of the program). The counts say which origin glsl/mem.py global_addr should follow.

Why: 48 of the 65 programs a run of Orbitals could not translate (17/11/2026) fail there: their draws are skipped, and
the title screen, menu and character select lose their backgrounds. The programs are the player's (ORBITALS_SPIRV_DUMP)
and stay on their machine; only the counts are printed.

--all looks at every dumped program (a check of the tool); --tex counts instead where the texture handles of the
programs refused with "texture handle in a register not traced to a constant bank" come from.

Usage (Windows, from the folder that holds orbitals-recomp.exe and setup\\; forward slashes, as a "\\n" in a pasted
path breaks the line):
    setup\\python\\python.exe setup/src/tools/shaders/base_origin.py --dumped spirv-dump [--spec FILE] [--depth N]
--spec defaults to the installation's sm86/instructions.json (made by dumped_shaders.py).
"""

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sm86/translate"))
sys.path.insert(0, str(ROOT / "tools/shaders"))

import glsl  # noqa: E402
from extract import sph_stage, trim  # noqa: E402
from program import Decoder  # noqa: E402

RZ, URZ = 255, 63
BASES = ("Ra_URb", "Ra_URc")


def consts(i) -> str:
    """The instruction's constant bank operands, c[bank][offset]."""
    out = []
    for k, iv in i.f.items():
        if k.startswith("ConstBankAddress"):
            (_, bank), (slot, addr) = iv.slot_values
            out.append(f"c[{bank:#x}][{addr * 4 if slot.width == 14 else addr:#x}]")   # 14 bits: words; 16: bytes
    return " ".join(out)


def writes(i, kind: str, n: int) -> bool:
    """i writes register n ("u" uniform, "r" general), a pair's high half included."""
    f = "URd" if kind == "u" else "Rd"
    if not i.has(f) or (kind == "r" and i.op in ("STG", "STS", "STL", "ST")):
        return False
    d = i.v(f)
    wide = any(s in i.cls for s in ("64", "128")) or i.sym("sz") in ("64", "128")
    return d == n or (wide and d + 1 == n) or (i.sym("sz") == "128" and d < n <= d + 3)


def origin(insns: list, at: int, kind: str, n: int, depth: int) -> list[str]:
    """The shapes of the writes behind register n before insns[at], newest first."""
    chain = []
    for _ in range(depth):
        j = next((k for k in range(at - 1, -1, -1) if writes(insns[k], kind, n)), None)
        if j is None:
            chain.append(f"(no write of {'UR' if kind == 'u' else 'R'} before: an input)")
            break
        w = insns[j]
        extra = f" lut {w.v('imm8'):#x}" if w.has("imm8") else ""
        if w.has("Rc"):
            extra += " Rc=RZ" if w.v("Rc") == RZ else " Rc=R"
        if w.v("Pg", 7) != 7 or w.v("Pg@not", 0):
            extra += " predicated"
        chain.append(f"{w.op} {w.cls} {consts(w)}{extra}".strip())
        nxt = next(((("u", w.v(r)) for r in ("URa", "URb", "URc") if w.has(r) and w.v(r) != URZ)), None) or next(
            (("r", w.v(r)) for r in ("Ra", "Rb", "Rc") if w.has(r) and w.v(r) != RZ), None
        )
        if nxt is None:
            break
        (kind, n), at = nxt, j
    return chain


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dumped", type=Path, required=True, help="the ORBITALS_SPIRV_DUMP folder of a run")
    ap.add_argument("--spec", type=Path, default=Path.cwd() / "sm86/instructions.json")
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--all", action="store_true", help="every dumped program, translated or not (a check of the tool)")
    ap.add_argument("--tex", action="store_true", help="texture handles in a register (tex.py tex_key) instead")
    a = ap.parse_args()
    if not a.spec.is_file():
        print(f"{a.spec} missing: run dumped_shaders.py once (it builds it), or give --spec", file=sys.stderr)
        return 1
    dec = Decoder(a.spec)
    shapes, progs, why = Counter(), Counter(), Counter()
    failing = 0
    for code in sorted(a.dumped.glob("*.code")):
        raw = code.read_bytes()
        stage = sph_stage(raw) or "cs"
        sph, insns = dec.program(trim(raw, stage), stage)
        ctl = code.with_suffix(".ctl")
        try:
            glsl.translate(sph, insns, stage, glsl.compute_shape(ctl.read_bytes()) if stage == "cs" else None, b"")
            if not a.all:
                continue
        except glsl.Unsupported as e:
            want = "texture handle in a register" if a.tex else "not a traced storage buffer"
            if want not in str(e) and not a.all:
                continue
            why[str(e)] += 1
        except Exception:   # noqa: BLE001 (a translator error is not this census's question)
            if not a.all:
                continue
        failing += 1
        seen = set()
        for k, i in enumerate(insns):
            if a.tex:   # texture instructions whose handle is a register: general (noConst) or uniform (_urc_)
                ur = next((f for f in ("URc", "URb") if "urc" in i.cls and i.has(f) and i.v(f) != URZ), None)
                if ur is None and ("noConst" not in i.cls or not i.has("Rb") or i.v("Rb") == RZ):
                    continue
                kind, reg = ("u", i.v(ur)) if ur else ("r", i.v("Rb"))
                chain = " <- ".join(origin(insns, k, kind, reg, a.depth))
                guard = " predicated" if i.v("Pg", 7) != 7 or i.v("Pg@not", 0) else ""
                shape = f"{i.op} {i.cls}{guard}: {'UR' if ur else 'R'} <- {chain}"
            else:
                base = next((i.v(f) for f in BASES if i.has(f)), None)
                if base is None or base == URZ:
                    continue
                chain = " <- ".join(origin(insns, k, "u", base, a.depth))
                shape = f"{i.op} {i.cls}: UR <- {chain}"
            shapes[shape] += 1
            if shape not in seen:
                seen.add(shape)
                progs[shape] += 1
    what = "texture handle" if a.tex else "base"
    print(f"{failing} dumped programs {'looked at' if a.all else f'fail on an untraced {what}'}")
    for w, c in why.most_common():
        print(f"  {c:4} {w}")
    print(f"{'register-handle texture instructions' if a.tex else 'uniform-base accesses'} in them, by the origin "
          f"of the {what} (instructions, programs):")
    for s, c in shapes.most_common(25):
        print(f"  {c:5} {progs[s]:4}  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
