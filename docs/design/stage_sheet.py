"""성장 단계 스프라이트 9종을 한 장에 그린다(README 미리보기용).

사용: python3 docs/design/stage_sheet.py   → docs/preview/stages-light.svg, stages-dark.svg
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from codetree_badge.levels import STAGES  # noqa: E402
from codetree_badge.pix import Pix  # noqa: E402
from codetree_badge.pixcard import THEMES  # noqa: E402
from codetree_badge.sprites import GH, GW, PALETTE, stage_sprite  # noqa: E402

U = 3                      # 스프라이트 셀 크기(배지는 4)
CELL_W, CELL_H = GW * U + 16, GH * U + 44
GAP, PAD = 6, 10


def sheet(theme: str) -> str:
    t = THEMES[theme]
    n = len(STAGES)
    w = PAD * 2 + n * CELL_W + (n - 1) * GAP
    h = PAD * 2 + CELL_H
    p = Pix()
    p.panel(0, 0, w, h, t["panel"], t["panel_stroke"])
    for i, (lv, name) in enumerate(STAGES):
        x = PAD + i * (CELL_W + GAP)
        p.panel(x, PAD, CELL_W, CELL_H, t["box"], t["box_stroke"])
        p.sprite(stage_sprite(i + 1), PALETTE, x + 8, PAD + 6, U)
        p.text(name, x + CELL_W // 2, PAD + GH * U + 24, "g7", 2, t["text"], "middle")
        p.text(f"Lv.{lv}", x + CELL_W // 2, PAD + GH * U + 38, "g7", 2, t["muted"], "middle")
    return p.svg(w, h, "성장 단계: " + ", ".join(f"Lv.{lv} {name}" for lv, name in STAGES))


if __name__ == "__main__":
    out = ROOT / "docs" / "preview"
    for theme in ("light", "dark"):
        (out / f"stages-{theme}.svg").write_text(sheet(theme), encoding="utf-8")
        print(out / f"stages-{theme}.svg")
