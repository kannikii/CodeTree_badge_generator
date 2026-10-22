"""BDF 비트맵 폰트에서 필요한 글리프만 뽑아 파이썬 모듈로 만든다.
사용: python3 -I bdf2py.py <out.py> <charset.txt> name=path.bdf ...
"""
import sys
from pathlib import Path


def parse_bdf(path: Path) -> tuple[dict, dict]:
    props, glyphs = {}, {}
    cur = None
    rows = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if rows is not None:
            if line.startswith("ENDCHAR"):
                cur["rows"] = rows
                glyphs[cur["enc"]] = cur
                cur, rows = None, None
            else:
                rows.append(line.strip())
            continue
        if line.startswith("STARTCHAR"):
            cur = {}
        elif line.startswith("ENCODING") and cur is not None:
            cur["enc"] = int(line.split()[1])
        elif line.startswith("DWIDTH") and cur is not None:
            cur["adv"] = int(line.split()[1])
        elif line.startswith("BBX") and cur is not None:
            w, h, xo, yo = map(int, line.split()[1:5])
            cur.update(w=w, h=h, xo=xo, yo=yo)
        elif line.startswith("BITMAP") and cur is not None:
            rows = []
        elif line.startswith("FONT_ASCENT"):
            props["ascent"] = int(line.split()[1])
        elif line.startswith("FONT_DESCENT"):
            props["descent"] = int(line.split()[1])
    return props, glyphs


def glyph_runs(g: dict) -> list[tuple[int, int, int]]:
    """(x, y, 길이) 가로 런 목록. y 는 베이스라인 기준 아래 방향(+)."""
    runs = []
    w, h = g["w"], g["h"]
    top = -(g["yo"] + h)
    for i, hexrow in enumerate(g["rows"]):
        bits = bin(int(hexrow, 16))[2:].zfill(len(hexrow) * 4)[:w]
        x = 0
        while x < w:
            if bits[x] == "1":
                start = x
                while x < w and bits[x] == "1":
                    x += 1
                runs.append((g["xo"] + start, top + i, x - start))
            else:
                x += 1
    return runs


def main():
    out, charset_file, *fonts = sys.argv[1:]
    chars = sorted(set(Path(charset_file).read_text(encoding="utf-8")) - {"\n", "\r"})
    lines = []
    missing = {}
    data = {}
    for spec in fonts:
        name, path = spec.split("=", 1)
        props, glyphs = parse_bdf(Path(path))
        table = {}
        for ch in chars:
            g = glyphs.get(ord(ch))
            if g is None:
                missing.setdefault(name, []).append(ch)
                continue
            table[ch] = (g["adv"], glyph_runs(g))
        data[name] = (props, table)
    lines.append('"""갈무리(Galmuri) 비트맵 폰트에서 배지에 필요한 글리프만 추출한 데이터(자동 생성).')
    lines.append("")
    lines.append("원본: https://github.com/quiple/galmuri (v2.40.4)")
    lines.append("Copyright (c) 2019–2025 Lee Minseo (quiple@quiple.dev), SIL Open Font License 1.1 — docs/fonts/OFL-Galmuri.txt")
    lines.append("생성: docs/fonts/build_pixfont.py")
    lines.append("")
    lines.append("형식: FONTS[이름] = (ascent, descent, {문자: (advance, ((x, y, 길이), ...))})")
    lines.append("x, y 는 베이스라인 원점 기준 픽셀 좌표(y 는 아래로 +), 길이는 가로 런 길이.")
    lines.append('"""')
    lines.append("")
    lines.append("FONTS = {")
    for name, (props, table) in data.items():
        lines.append(f'    "{name}": ({props["ascent"]}, {props["descent"]}, {{')
        for ch, (adv, runs) in table.items():
            runs_s = ", ".join(f"({x},{y},{n})" for x, y, n in runs)
            if len(runs) == 1:
                runs_s += ","
            lines.append(f"        {ch!r}: ({adv}, ({runs_s})),")
        lines.append("    }),")
    lines.append("}")
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, chs in missing.items():
        print(f"{name}: 없는 글리프 {len(chs)}개: {''.join(chs)}")
    print(f"{out}: {len(chars)}자 × {len(data)}폰트, {Path(out).stat().st_size} bytes")


if __name__ == "__main__":
    main()
