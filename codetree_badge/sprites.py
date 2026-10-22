"""키우기 캐릭터(성장 단계별 나무) 도트 스프라이트.

32×28 문자 격자를 절차적으로 그린다. 글자 → 색 대응은 PALETTE 에 있다.
"""

from __future__ import annotations

GW, GH = 32, 28
GROUND = 23  # 흙 더미 윗줄

PALETTE = {
    "d": "#1B6B3A",  # 잎 외곽선
    "G": "#2FB869",  # 잎 (코드트리 초록)
    "g": "#229A55",  # 잎 그늘
    "h": "#7BE3A3",  # 잎 하이라이트
    "k": "#4A2E14",  # 줄기·흙 외곽선
    "B": "#9A6436",  # 줄기
    "b": "#6E4321",  # 줄기 그늘
    "S": "#C9A070",  # 흙
    "s": "#A47A4D",  # 흙 그늘
    "R": "#F0553F",  # 열매
    "P": "#F8A5C2",  # 꽃잎
    "p": "#FFE27A",  # 꽃 중심
    "Y": "#F7C948",  # 반짝임
    "W": "#FFFFFF",  # 하이라이트
    "U": "#486DF6",  # 파랑 포인트 (코드트리 파랑)
}
LEAF = set("Gghp P".replace(" ", "")) | {"P"}
WOOD = set("BbSs")


def _blank():
    return [["."] * GW for _ in range(GH)]


def _put(g, x, y, c):
    if 0 <= x < GW and 0 <= y < GH:
        g[y][x] = c


def _ellipse(g, cx, cy, rx, ry, c="G"):
    for y in range(GH):
        for x in range(GW):
            if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1.0:
                _put(g, x, y, c)


def _soil(g):
    for i, y in enumerate(range(GROUND, GH)):
        half = (5, 8, 11, 13, 15)[i]
        for x in range(16 - half, 16 + half):
            _put(g, x, y, "s" if y >= GH - 1 or (y == GROUND + 2 and x % 7 == 3) else "S")


def _trunk(g, x0, x1, top, bottom=GROUND):
    for y in range(top, bottom + 1):
        for x in range(x0, x1 + 1):
            _put(g, x, y, "b" if x == x1 else "B")


def _stem(g, x, top, bottom=GROUND):
    for y in range(top, bottom + 1):
        _put(g, x, y, "g")


def _shade_canopy(g, cx, cy, rx, ry):
    """잎 영역의 오른쪽 아래를 그늘(g), 왼쪽 위 몇 점을 하이라이트(h) 로."""
    for y in range(GH):
        for x in range(GW):
            if g[y][x] != "G":
                continue
            u, v = (x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry
            if u + v > 0.55:
                g[y][x] = "g"
            elif u + v < -0.9 and u < -0.2:
                g[y][x] = "h"


def _fruits(g, spots):
    for x, y in spots:
        if g[y][x] in "Ggh" and g[y][x + 1] in "Ggh" and g[y + 1][x] in "Ggh" and g[y + 1][x + 1] in "Ggh":
            _put(g, x, y, "W"); _put(g, x + 1, y, "R"); _put(g, x, y + 1, "R"); _put(g, x + 1, y + 1, "R")


def _flowers(g, spots):
    for x, y in spots:
        ok = all(g[y + dy][x + dx] in "Ggh" for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))
        if ok:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                _put(g, x + dx, y + dy, "P")
            _put(g, x, y, "p")


def _sparkles(g, spots):
    for x, y in spots:
        if all(g[y + dy][x + dx] == "." for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))):
            for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                _put(g, x + dx, y + dy, "Y")
            _put(g, x, y, "W")


def _outline(g):
    out = [row[:] for row in g]
    for y in range(GH):
        for x in range(GW):
            if g[y][x] != ".":
                continue
            near = [g[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= x + dx < GW and 0 <= y + dy < GH]
            if any(c in "GghPp" for c in near):
                out[y][x] = "d"
            elif any(c in "BbSs" for c in near):
                out[y][x] = "k"
    return out


def _seed(g):
    for x in range(14, 18):
        _put(g, x, 20, "B")
    for x in range(13, 19):
        _put(g, x, 21, "B")
    for x in range(14, 18):
        _put(g, x, 22, "b")
    _put(g, 14, 20, "W"); _put(g, 15, 20, "W")
    _put(g, 18, 21, "b")


def _leaf(g, cx, cy, rx, ry):
    _ellipse(g, cx, cy, rx, ry, "G")


def stage_sprite(stage: int) -> list[str]:
    """stage 1~9 의 32×28 스프라이트(문자 행 목록)."""
    g = _blank()
    _soil(g)
    if stage == 1:            # 씨앗
        _seed(g)
    elif stage == 2:          # 새싹
        _stem(g, 16, 18)
        _leaf(g, 13.5, 17.5, 3.0, 1.6)
        _leaf(g, 19.0, 16.5, 3.0, 1.6)
        _put(g, 16, 17, "G"); _put(g, 16, 16, "G")
    elif stage == 3:          # 묘목
        _stem(g, 16, 12)
        _leaf(g, 13.0, 19.0, 3.2, 1.6)
        _leaf(g, 19.5, 17.0, 3.2, 1.6)
        _leaf(g, 13.0, 15.0, 3.2, 1.6)
        _leaf(g, 19.5, 13.5, 3.0, 1.6)
        _leaf(g, 16.5, 11.0, 2.2, 1.8)
    elif stage == 4:          # 어린 나무
        _trunk(g, 15, 16, 16)
        _ellipse(g, 16, 12.5, 6.0, 5.0)
        _shade_canopy(g, 16, 12.5, 6.0, 5.0)
    elif stage == 5:          # 나무
        _trunk(g, 15, 17, 15)
        _ellipse(g, 11, 14, 4.5, 3.5)
        _ellipse(g, 21.5, 14, 4.5, 3.5)
        _ellipse(g, 16, 10.5, 8.0, 6.0)
        _shade_canopy(g, 16, 11, 9.0, 7.0)
    elif stage >= 6:          # 큰 나무 / 꽃나무 / 열매 나무 / 거목
        big = stage >= 9
        tw = 4 if big else 3
        _trunk(g, 16 - tw // 2, 16 - tw // 2 + tw - 1, 14 if big else 15)
        if big:
            for x in (13, 19):
                _put(g, x, GROUND, "B"); _put(g, x, GROUND - 1, "B")
        _ellipse(g, 8.5 if big else 9.5, 14.5, 6.0 if big else 5.0, 4.0)
        _ellipse(g, 23.5 if big else 22.5, 14.5, 6.0 if big else 5.0, 4.0)
        _ellipse(g, 16, 9.5, 11.0 if big else 10.0, 7.0 if big else 6.5)
        _ellipse(g, 16, 5.0 if big else 6.0, 7.0 if big else 6.0, 4.0)
        _shade_canopy(g, 16, 10, 12.0, 8.0)
        if stage == 7:
            _flowers(g, [(9, 11), (16, 5), (22, 12), (13, 16), (20, 17), (16, 11)])
        if stage == 8:
            _fruits(g, [(8, 12), (14, 7), (21, 10), (12, 15), (19, 15), (16, 12)])
        if big:
            _fruits(g, [(7, 13), (13, 6), (21, 8), (11, 16), (19, 16), (16, 11), (25, 15)])
            _sparkles(g, [(3, 4), (29, 7), (26, 2), (2, 13)])
    g = _outline(g)
    return ["".join(row) for row in g]
