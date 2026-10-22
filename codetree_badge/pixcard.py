"""도트풍 카드(일일 경험치·성장 레벨)가 함께 쓰는 색·치수."""

from __future__ import annotations

from .render import THEMES as BASE

# 기본 배지 테마 색에 입체 블록용 밝은/어두운 색을 더한다 (코드트리 초록·파랑 계열)
THEMES = {
    "light": dict(BASE["light"], green_light="#7BE3A3", green_shade="#1B6B3A",
                  blue_light="#9DB2FF", blue_shade="#2A47B3",
                  track="#DEDEDE", track_shade="#C8C8C8", track_light="#EDEDED",
                  box="#FFFFFF", box_stroke="#D9D9D9", line="#E3E3E3", soil="#C9A070"),
    "dark": dict(BASE["dark"], green_light="#7BE3A3", green_shade="#1B6B3A",
                 blue_light="#9DB2FF", blue_shade="#2A47B3",
                 track="#2D333B", track_shade="#21262D", track_light="#3A414A",
                 box="#0D1117", box_stroke="#30363D", line="#30363D", soil="#C9A070"),
}

P = 24          # 카드 안쪽 여백(픽셀 격자 기준)
TITLE_Y = 36    # 제목 베이스라인 (기본 배지와 같은 높이)
