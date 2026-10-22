"""성장 레벨 카드 (도트풍): 누적 경험치로 계산한 레벨과 단계별로 자라는 나무 캐릭터."""

from __future__ import annotations

from .levels import STAGES, LevelInfo
from .pix import Pix, text_width
from .pixcard import P, THEMES, TITLE_Y
from .progress import Report
from .sprites import GH, GW, PALETTE, stage_sprite

W = 200
H = 272
CELL = 4                  # 스프라이트 1칸 = 4px (32×28 → 128×112)
BOX_Y = 44
BOX_H = GH * CELL + 8
HUD_Y = BOX_Y + BOX_H + 30   # "Lv.N" 베이스라인
BAR_Y = HUD_Y + 10
BAR_H = 12


def summary_text(lv: LevelInfo) -> str:
    nxt = f", Lv.{lv.next_stage_level} 에 {STAGES[lv.stage][1]}" if lv.next_stage_level else ""
    return f"성장 레벨: Lv.{lv.level} {lv.stage_name}, 다음 레벨까지 {lv.remaining} XP, 누적 {lv.total} XP{nxt}"


def render_level(rep: Report, theme: str = "light") -> str:
    t = THEMES[theme]
    lv = rep.xp.level
    p = Pix()
    p.panel(0, 0, W, H, t["panel"], t["panel_stroke"])

    # 제목 + 단계 핍(지나온 단계는 초록)
    p.text("성장 레벨", P, TITLE_Y, "g9", 2, t["text"])
    pip_x = W - P - (len(STAGES) * 6 - 2)
    for i in range(len(STAGES)):
        p.rect(pip_x + i * 6, TITLE_Y - 14, 4, 4, t["green"] if i < lv.stage else t["track_shade"])

    # 캐릭터 창
    box_w = W - 2 * P
    p.panel(P, BOX_Y, box_w, BOX_H, t["box"], t["box_stroke"])
    p.sprite(stage_sprite(lv.stage), PALETTE, P + (box_w - GW * CELL) // 2, BOX_Y + 4, CELL)

    # HUD 줄: 왼쪽 Lv.N, 오른쪽 단계 이름 칩
    num = str(lv.level)
    lv_w = text_width("Lv.", "g9", 2)
    p.text("Lv.", P, HUD_Y, "g9", 2, t["muted"])
    p.text(num, P + lv_w + 4, HUD_Y, "g11b", 2, t["text"])
    hud_end = P + lv_w + 4 + text_width(num, "g11b", 2)
    name_w = text_width(lv.stage_name, "g7", 2)
    pad = 8 if W - P - (name_w + 16) - hud_end >= 8 else 5
    chip_w = name_w + pad * 2
    chip_x = W - P - chip_w
    p.panel(chip_x, HUD_Y - 20, chip_w, 20, t["green"], t["green_shade"])
    p.text(lv.stage_name, chip_x + pad, HUD_Y - 5, "g7", 2, "#FFFFFF")

    # 다음 레벨까지 진행 바 + 수치
    bar_w = W - 2 * P
    p.rect(P, BAR_Y, bar_w, BAR_H, t["track_shade"])
    p.rect(P + 2, BAR_Y + 2, bar_w - 4, BAR_H - 4, t["track"])
    fill_w = round((bar_w - 4) * min(lv.pct, 100) / 100 / 2) * 2
    if fill_w > 0:
        p.block(P + 2, BAR_Y + 2, fill_w, BAR_H - 4, t["blue"], t["blue_shade"], t["blue_light"])
    row_a = BAR_Y + BAR_H + 18
    row_b = row_a + 18
    prog, total, pct = f"{lv.xp} / {lv.need} XP", f"누적 {lv.total} XP", f"{lv.pct:.0f}%"
    p.text(prog, P, row_a, "g7", 2, t["text"])
    p.text(total, P, row_b, "g7", 2, t["muted"])
    # 퍼센트는 진행 줄 오른쪽에, 자리가 없으면(레벨 100 이상 등) 누적 줄 오른쪽에, 그래도 없으면 생략한다.
    pct_w = text_width(pct, "g7", 2)
    for text, y in ((prog, row_a), (total, row_b)):
        if P + text_width(text, "g7", 2) + 8 + pct_w <= W - P:
            p.text(pct, W - P, y, "g7", 2, t["muted"], "end")
            break
    return p.svg(W, H, summary_text(lv))
