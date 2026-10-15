"""Report → SVG (라이트/다크). 좌표·색·도형 규칙은 docs/design/design_reference.py 를 따른다."""

from __future__ import annotations

import html
import math

from .progress import CURRENT, DONE, STARTED, TEST_DONE, Report

FONT = ("-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Pretendard','Noto Sans KR',"
        "'Noto Sans CJK KR','Malgun Gothic','Segoe UI',sans-serif")

THEMES = {
    "light": dict(panel="#F5F5F5", panel_stroke="#E8E8E8", card="#FFFFFF", card_stroke="#EDEDED",
                  text="#2B2B2B", sub="#414141", muted="#8A8A8A", gray="#DEDEDE", green="#2FB869",
                  pie_track="#D5F3D9", pie="#2DC43F", bar_track="#DEDEDE", blue="#486DF6",
                  chip_bg="#DAE6FE", chip_stroke="#BED4FE", chip_text="#486DF6"),
    "dark": dict(panel="#161B22", panel_stroke="#30363D", card="#0D1117", card_stroke="#262C36",
                 text="#E6EDF3", sub="#C9D1D9", muted="#8B949E", gray="#2D333B", green="#2FB869",
                 pie_track="#1C3A28", pie="#2DC43F", bar_track="#2D333B", blue="#6E8BFF",
                 chip_bg="#1A2547", chip_stroke="#2C3D73", chip_text="#8EA6FF"),
}

W = 560                 # 전체 폭
P = 16                  # 패널 안쪽 여백
HX_PITCH = 14           # 레슨 육각형 가로 간격
GROUP_GAP = 5           # 5개 묶음 사이 추가 간격
ROW_PITCH = 13          # 줄 간격
PER_ROW = 32            # 한 줄 최대 레슨 수
STRIP_PITCH = 8.6       # 스트릭 스트립 간격
ELLIPSIS = "…"

_CLASS = {DONE: "done", TEST_DONE: "test", STARTED: "ring", CURRENT: "cur"}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def tw(s: str, size: float) -> float:
    """대략적인 텍스트 폭(px). 한글·전각 1em, 영문·숫자 약 0.56em."""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3 or 0x3040 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF:
            w += 1.0
        elif ch == " ":
            w += 0.3
        elif ch in "il.,:;·|!'()[]":
            w += 0.32
        elif ch.isupper() or ch in "%mwMW@#…":
            w += 0.68
        else:
            w += 0.56
    return w * size


def fit(s: str, size: float, max_w: float) -> str:
    """max_w 를 넘으면 뒤를 잘라 말줄임표를 붙인다."""
    if tw(s, size) <= max_w:
        return s
    while s and tw(s + ELLIPSIS, size) > max_w:
        s = s[:-1]
    return s.rstrip() + ELLIPSIS


def hex_pts(r: float) -> str:
    """pointy-top 정육각형 꼭짓점(중심 0,0)."""
    return " ".join(f"{r * math.cos(math.radians(a)):.2f},{r * math.sin(math.radians(a)):.2f}"
                    for a in (-90, -30, 30, 90, 150, 210))


def pie(cx: float, cy: float, r: float, ratio: float, t: dict) -> str:
    """12시 방향에서 시계 방향으로 채우는 파이."""
    out = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{t["pie_track"]}"/>'
    if ratio >= 0.9995:
        return out + f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{t["pie"]}"/>'
    if ratio <= 0:
        return out
    a = math.radians(-90 + 360 * ratio)
    x, y = cx + r * math.cos(a), cy + r * math.sin(a)
    return out + (f'<path d="M{cx},{cy} L{cx},{cy - r} A{r},{r} 0 {1 if ratio > 0.5 else 0} 1 {x:.2f},{y:.2f} Z" '
                  f'fill="{t["pie"]}"/>')


def icon(cls: str, x: float, y: float) -> str:
    if cls == "test":  # 외곽선 + 안쪽 작은 육각형
        return (f'<use xlink:href="#hr" x="{x:.1f}" y="{y:.1f}" class="ring"/>'
                f'<use xlink:href="#hd" x="{x:.1f}" y="{y:.1f}" class="dot"/>')
    if cls in ("ring", "cur"):
        return f'<use xlink:href="#hr" x="{x:.1f}" y="{y:.1f}" class="{cls}"/>'
    return f'<use xlink:href="#h" x="{x:.1f}" y="{y:.1f}" class="{cls}"/>'


def summary_text(rep: Report) -> str:
    d = rep.display
    return (f"코드트리 학습 현황: Trail {d.no} {d.pct:.1f}% 완료, 전체 {rep.pct:.1f}%, "
            f"현재 연속 {rep.streak.current}일")


def render(rep: Report, theme: str = "light") -> str:
    t = THEMES[theme]
    d = rep.display
    states = d.pattern or "."
    rows = max(1, math.ceil(len(states) / PER_ROW))

    cy0 = 80                                        # 트레일 카드 y
    card_h = 58 + (rows - 1) * ROW_PITCH + 26
    sk_y = cy0 + card_h + 10                        # 스트릭 카드 y
    sk_h = 64
    H = sk_y + sk_h + 34
    cx0, cw = P, W - 2 * P

    css = (f'text{{font-family:{FONT}}}'
           f'.done{{fill:{t["green"]};stroke:{t["green"]};stroke-width:1.4;stroke-linejoin:round}}'
           f'.todo{{fill:{t["gray"]};stroke:{t["gray"]};stroke-width:1.4;stroke-linejoin:round}}'
           f'.ring{{fill:{t["card"]};stroke:{t["green"]};stroke-width:1.7;stroke-linejoin:round}}'
           f'.cur{{fill:{t["card"]};stroke:{t["blue"]};stroke-width:1.7;stroke-linejoin:round}}'
           f'.dot{{fill:{t["green"]}}}'
           f'.sdone{{fill:{t["green"]}}}.stodo{{fill:{t["gray"]}}}'
           f'.today{{fill:none;stroke:{t["text"]};stroke-width:1.1;stroke-opacity:.55}}')
    summary = esc(summary_text(rep))
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
         f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{summary}">',
         f'<title>{summary}</title>',
         f'<defs><style>{css}</style>'
         f'<polygon id="h" points="{hex_pts(6.0)}"/><polygon id="hr" points="{hex_pts(5.8)}"/>'
         f'<polygon id="hd" points="{hex_pts(2.6)}"/><polygon id="hs" points="{hex_pts(4.0)}"/>'
         f'<polygon id="hso" points="{hex_pts(5.6)}"/></defs>',
         f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["panel"]}" stroke="{t["panel_stroke"]}"/>']

    # ── 헤더: 제목 + 전체 진행률
    o.append(f'<text x="{P + 8}" y="36" font-size="15" font-weight="700" fill="{t["text"]}">코드트리 학습 현황</text>')
    ov = f"전체 {rep.pct:.1f}% 완료됨"
    bx = W - P - 8 - tw(ov, 12) - 10 - 72
    o.append(f'<rect x="{bx:.1f}" y="27.5" width="72" height="6" rx="3" fill="{t["bar_track"]}"/>')
    if rep.pct > 0:
        o.append(f'<rect x="{bx:.1f}" y="27.5" width="{max(6.0, 72 * rep.pct / 100):.1f}" height="6" rx="3" fill="{t["green"]}"/>')
    o.append(f'<text x="{W - P - 8}" y="35" font-size="12" text-anchor="end" fill="{t["sub"]}">{esc(ov)}</text>')

    # ── 범례
    lx = P + 8 + 6
    for cls, label in (("done", "완료됨"), ("test", "테스트 완료"), ("ring", "시작됨"), ("todo", "시작하지 않음")):
        o.append(icon(cls, lx, 61))
        o.append(f'<text x="{lx + 11}" y="65" font-size="12" fill="{t["sub"]}">{label}</text>')
        lx += 11 + tw(label, 12) + 18

    # ── 트레일 카드
    o.append(f'<rect x="{cx0}" y="{cy0}" width="{cw}" height="{card_h}" rx="12" fill="{t["card"]}" stroke="{t["card_stroke"]}"/>')
    tx = cx0 + 20
    title = f"Trail {d.no}"
    o.append(f'<text x="{tx}" y="{cy0 + 33}" font-size="18" font-weight="500" fill="{t["text"]}">{esc(title)}</text>')
    pr = 14
    pcx, pcy = cx0 + cw - 20 - pr, cy0 + 28
    right = f"{d.passed} / {d.total} · {d.pct:.1f}% 완료됨"
    right_x = pcx - pr - 12
    sx = tx + tw(title, 18) + 8
    chip = "현재 학습 중" if rep.is_current else ""
    chip_w = tw(chip, 12) + 16 if chip else 0
    room = max(right_x - tw(right, 13) - 14 - sx - (chip_w + 10 if chip else 0), 40)
    # 공간이 모자라면 한글 트레일명을 빼고 영문 레벨만, 그래도 모자라면 말줄임
    options = [f"{d.level} · {d.name}", d.level] if d.name else [d.level]
    sub = next((s for s in options if tw(s, 12) <= room), fit(d.level, 12, room))
    o.append(f'<text x="{sx:.1f}" y="{cy0 + 33}" font-size="12" fill="{t["muted"]}">{esc(sub)}</text>')
    if chip:
        chx = sx + tw(sub, 12) + 10
        o.append(f'<rect x="{chx:.1f}" y="{cy0 + 18}" width="{chip_w:.1f}" height="22" rx="6" '
                 f'fill="{t["chip_bg"]}" stroke="{t["chip_stroke"]}"/>')
        o.append(f'<text x="{chx + chip_w / 2:.1f}" y="{cy0 + 33}" font-size="12" text-anchor="middle" '
                 f'fill="{t["chip_text"]}">{chip}</text>')
    o.append(pie(pcx, pcy, pr, d.pct / 100, t))
    o.append(f'<text x="{right_x}" y="{cy0 + 33}" font-size="13" text-anchor="end" fill="{t["sub"]}">{esc(right)}</text>')

    # ── 레슨 육각형 그리드: 5개 묶음은 전체 인덱스 기준(줄이 바뀌어도 묶음이 이어진다)
    gx0, gy0 = tx + 6, cy0 + 60
    for i, s in enumerate(states):
        r, c = divmod(i, PER_ROW)
        x = gx0 + c * HX_PITCH + (i // 5 - (r * PER_ROW) // 5) * GROUP_GAP
        o.append(icon(_CLASS.get(s, "todo"), x, gy0 + r * ROW_PITCH))

    # ── 스트릭 카드
    st = rep.streak
    o.append(f'<rect x="{cx0}" y="{sk_y}" width="{cw}" height="{sk_h}" rx="12" fill="{t["card"]}" stroke="{t["card_stroke"]}"/>')
    sxp = cx0 + 20
    for label, val, highlight in (("현재 연속", st.current, True), ("최장 연속", st.best, False), ("총 학습일", st.total, False)):
        col = t["green"] if (highlight and val > 0) else t["text"]
        o.append(f'<text x="{sxp}" y="{sk_y + 30}" font-size="20" font-weight="700" fill="{col}">{val}'
                 f'<tspan font-size="12" font-weight="500" fill="{t["sub"]}" dx="2">일</tspan></text>')
        o.append(f'<text x="{sxp}" y="{sk_y + 49}" font-size="11" fill="{t["muted"]}">{label}</text>')
        sxp += 74
    x_end = cx0 + cw - 20 - 4
    x_start = x_end - (len(st.strip) - 1) * STRIP_PITCH
    o.append(f'<text x="{x_end + 4}" y="{sk_y + 22}" font-size="10.5" text-anchor="end" fill="{t["muted"]}">최근 4주</text>')
    for k, on in enumerate(st.strip):
        x = x_start + k * STRIP_PITCH
        o.append(f'<use xlink:href="#hs" x="{x:.1f}" y="{sk_y + 40}" class="{"sdone" if on else "stodo"}"/>')
        if k == len(st.strip) - 1:  # 오늘
            o.append(f'<use xlink:href="#hso" x="{x:.1f}" y="{sk_y + 40}" class="today"/>')

    # ── 푸터
    fy = sk_y + sk_h + 21
    stamp = rep.today.strftime("%Y.%m.%d")
    right_footer = (f"Trail {d.no} 고정 · {stamp}" if rep.mode == "fixed" else f"가장 많이 푼 트레일 기준 · {stamp}")
    left_max = (W - 2 * (P + 8)) - tw(right_footer, 10.5) - 16
    prefix = "최근 통과 · "
    if rep.recent is None:
        left = prefix + "아직 없음"
    else:
        rc = rep.recent
        where = f"Trail {rc.trail_no} · {rc.lesson}" if rc.trail_no is not None and rc.lesson else (
            f"Trail {rc.trail_no}" if rc.trail_no is not None else rc.lesson)
        body = f"{rc.title} ({where})" if where else rc.title
        suffix = f" · {rc.day.strftime('%m.%d')}"
        left = prefix + fit(body, 10.5, left_max - tw(prefix, 10.5) - tw(suffix, 10.5)) + suffix
    o.append(f'<text x="{P + 8}" y="{fy}" font-size="10.5" fill="{t["muted"]}">{esc(left)}</text>')
    o.append(f'<text x="{W - P - 8}" y="{fy}" font-size="10.5" text-anchor="end" fill="{t["muted"]}">{esc(right_footer)}</text>')
    o.append("</svg>")
    return "".join(o) + "\n"
