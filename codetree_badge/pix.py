"""도트(8비트)풍 SVG 그리기 도구.

픽셀 폰트 텍스트(갈무리 비트맵 글리프 → <path>), 계단 모서리 사각형, 입체감 있는 블록,
스프라이트(문자 격자 → 픽셀 rect) 를 만든다. 좌표는 모두 정수 픽셀이며
shape-rendering="crispEdges" 로 흐림 없이 그린다.
"""

from __future__ import annotations

import html

from .pixfont import FONTS

FALLBACK = "?"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def _glyph(font: str, ch: str):
    table = FONTS[font][2]
    return table.get(ch) or table[FALLBACK]


def text_width(s: str, font: str = "g9", scale: int = 2) -> int:
    """텍스트 폭(px). 마지막 글자의 advance 까지 포함한다."""
    return sum(_glyph(font, ch)[0] for ch in s) * scale


def text_height(font: str, scale: int = 2) -> int:
    asc, desc, _ = FONTS[font]
    return (asc + desc) * scale


def missing_glyphs(s: str, font: str = "g9") -> str:
    table = FONTS[font][2]
    return "".join(sorted({ch for ch in s if ch not in table}))


def glyph_path(runs) -> str:
    return "".join(f"M{x} {y}h{n}v1h-{n}z" for x, y, n in runs)


class Pix:
    """한 SVG 의 본문과 <defs>(글리프 정의) 를 모은다."""

    def __init__(self):
        self.defs: dict[str, str] = {}
        self.body: list[str] = []

    def add(self, s: str) -> None:
        self.body.append(s)

    # ---- 텍스트 ----
    def text(self, s: str, x: int, y: int, font: str = "g9", scale: int = 2, fill: str = "#000",
             anchor: str = "start") -> int:
        """베이스라인 (x, y) 에 픽셀 폰트로 s 를 그린다. anchor: start | middle | end. 폭을 돌려준다."""
        w = text_width(s, font, scale)
        if anchor == "middle":
            x -= w // 2
        elif anchor == "end":
            x -= w
        uses = []
        cx = 0
        for ch in s:
            adv, runs = _glyph(font, ch)
            if runs:
                gid = f"{font}-{ord(ch if ch in FONTS[font][2] else FALLBACK):x}"
                self.defs.setdefault(gid, f'<path id="{gid}" d="{glyph_path(runs)}"/>')
                uses.append(f'<use href="#{gid}" x="{cx}"/>')
            cx += adv
        if uses:
            self.body.append(f'<g transform="translate({x} {y}) scale({scale})" fill="{fill}">{"".join(uses)}</g>')
        return w

    # ---- 도형 ----
    @staticmethod
    def rrect_path(x: int, y: int, w: int, h: int, u: int) -> str:
        """모서리를 두 계단(u, 2u) 으로 깎은 '픽셀 둥근' 사각형 경로."""
        return (f"M{x + 2 * u} {y}h{w - 4 * u}v{u}h{u}v{u}h{u}v{h - 4 * u}h-{u}v{u}h-{u}v{u}"
                f"h-{w - 4 * u}v-{u}h-{u}v-{u}h-{u}v-{h - 4 * u}h{u}v-{u}h{u}z")

    def panel(self, x: int, y: int, w: int, h: int, fill: str, stroke: str, u: int = 2) -> None:
        """테두리 두께 u 의 픽셀 둥근 패널."""
        self.body.append(f'<path fill="{fill}" d="{self.rrect_path(x, y, w, h, u)}"/>')
        self.body.append(f'<path fill="{stroke}" fill-rule="evenodd" d="{self.rrect_path(x, y, w, h, u)}'
                         f'{self.rrect_path(x + u, y + u, w - 2 * u, h - 2 * u, u)}"/>')

    def rect(self, x: int, y: int, w: int, h: int, fill: str) -> None:
        if w > 0 and h > 0:
            self.body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>')

    def block(self, x: int, y: int, w: int, h: int, fill: str, shade: str, light: str, u: int = 2) -> None:
        """오른쪽·아래 그림자, 왼쪽·위 하이라이트가 있는 입체 블록."""
        self.rect(x, y, w, h, fill)
        if w > 2 * u and h > 2 * u:
            self.rect(x + w - u, y + u, u, h - u, shade)
            self.rect(x + u, y + h - u, w - u, u, shade)
            self.rect(x, y, w - u, u, light)
            self.rect(x, y, u, h - u, light)

    def dashes(self, x1: int, x2: int, y: int, fill: str, u: int = 2, on: int = 3, off: int = 2) -> None:
        """u 두께 가로 점선. on/off 는 픽셀 단위(u) 개수."""
        x = x1
        while x < x2:
            self.rect(x, y, min(on * u, x2 - x), u, fill)
            x += (on + off) * u

    def sprite(self, rows: list[str], palette: dict[str, str], x: int, y: int, u: int = 4) -> None:
        """문자 격자 스프라이트. 같은 색 가로 런을 rect 하나로 합친다."""
        for j, row in enumerate(rows):
            i = 0
            while i < len(row):
                ch = row[i]
                if ch not in palette:
                    i += 1
                    continue
                k = i
                while k < len(row) and row[k] == ch:
                    k += 1
                self.rect(x + i * u, y + j * u, (k - i) * u, u, palette[ch])
                i = k

    # ---- 출력 ----
    def svg(self, w: int, h: int, title: str) -> str:
        defs = "".join(self.defs[k] for k in sorted(self.defs))
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
                f'role="img" aria-label="{esc(title)}" shape-rendering="crispEdges">'
                f'<title>{esc(title)}</title><defs>{defs}</defs>{"".join(self.body)}</svg>\n')
