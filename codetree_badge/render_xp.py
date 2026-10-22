"""일일 경험치 카드 (도트풍): 최근 14일 막대 + 목표선 + 오늘의 목표 진행 바."""

from __future__ import annotations

from .pix import Pix, text_width
from .pixcard import P, THEMES, TITLE_Y
from .progress import Report, XPStats

W = 560
H = 224
SLOT = 36        # 하루 칸 너비
BAR_W = 24       # 막대 너비
BAR_MAX = 80     # 가장 높은 막대
BASE_Y = 148     # 막대 바닥
ROW_Y = 192      # 오늘 진행 바 윗변


def summary_text(x: XPStats) -> str:
    return (f"일일 경험치: 오늘 {x.today}/{x.goal} XP, 최근 {len(x.days)}일 중 {x.goal_days}일 목표 달성, "
            f"최고 {x.best} XP, 누적 {x.total} XP")


def _colors(t: dict, done: bool) -> tuple[str, str, str]:
    return ((t["green"], t["green_shade"], t["green_light"]) if done
            else (t["blue"], t["blue_shade"], t["blue_light"]))


def render_xp(rep: Report, theme: str = "light") -> str:
    t = THEMES[theme]
    x = rep.xp
    n = len(x.days)
    p = Pix()
    p.panel(0, 0, W, H, t["panel"], t["panel_stroke"])

    # 제목 줄: 왼쪽 제목, 오른쪽 목표선 범례
    p.text("일일 경험치", P, TITLE_Y, "g9", 2, t["text"])
    legend = f"목표 {x.goal} XP · 최근 {n}일"
    lw = text_width(legend, "g7", 2)
    p.text(legend, W - P, TITLE_Y, "g7", 2, t["muted"], "end")
    p.dashes(W - P - lw - 30, W - P - lw - 10, TITLE_Y - 8, t["muted"])

    # 막대 차트: 목표 달성일은 초록, 미달은 파랑, 없는 날은 바닥 표시만
    chart_w = SLOT * n
    x0 = (W - chart_w) // 2
    scale_max = max(x.goal * 5 // 4, x.best, 1)
    p.rect(x0, BASE_Y, chart_w, 2, t["line"])
    for i, d in enumerate(x.days):
        bx = x0 + i * SLOT + (SLOT - BAR_W) // 2
        is_today = i == n - 1
        if d.xp <= 0:
            p.rect(bx, BASE_Y - 2, BAR_W, 2, t["track"])
        else:
            h = max(4, round(d.xp / scale_max * BAR_MAX / 2) * 2)
            done = bool(x.goal) and d.xp >= x.goal
            p.block(bx, BASE_Y - h, BAR_W, h, *_colors(t, done))
            p.text(str(d.xp), bx + BAR_W // 2, BASE_Y - h - 6, "g7", 2, t["sub"] if done else t["muted"], "middle")
        p.text("오늘" if is_today else str(d.day.day), bx + BAR_W // 2, BASE_Y + 20, "g7", 2,
               t["text"] if is_today else t["muted"], "middle")
    if x.goal:
        gy = BASE_Y - round(min(x.goal, scale_max) / scale_max * BAR_MAX / 2) * 2
        p.dashes(x0, x0 + chart_w, gy - 2, t["muted"])

    # 구분선 + 오늘의 목표 진행 바
    p.rect(P, ROW_Y - 14, W - 2 * P, 2, t["line"])
    done = bool(x.goal) and x.today >= x.goal
    p.text("오늘", P, ROW_Y + 12, "g7", 2, t["muted"])
    bar_x, bar_w, bar_h = P + 44, 180, 14
    p.rect(bar_x, ROW_Y, bar_w, bar_h, t["track_shade"])
    p.rect(bar_x + 2, ROW_Y + 2, bar_w - 4, bar_h - 4, t["track"])
    fill_w = round((bar_w - 4) * x.today_pct / 100 / 2) * 2
    if fill_w > 0:
        p.block(bar_x + 2, ROW_Y + 2, fill_w, bar_h - 4, *_colors(t, done))
    right = f"목표 달성 {x.goal_days}/{n}일"
    right_x = W - P - text_width(right, "g7", 2)
    status_x = bar_x + bar_w + 10
    status = f"{x.today} / {x.goal} XP"
    if done and status_x + text_width(status + " 달성!", "g7", 2) + 8 <= right_x:
        status += " 달성!"
    p.text(status, status_x, ROW_Y + 12, "g7", 2, t["green"] if done else t["text"])
    p.text(right, W - P, ROW_Y + 12, "g7", 2, t["muted"], "end")
    return p.svg(W, H, summary_text(x))
