"""누적 경험치 → 레벨·성장 단계.

레벨 L 에서 L+1 로 가는 데 필요한 경험치는 20L + 30 (Lv1→2: 50, Lv2→3: 70, …).
레벨 L 에 도달하는 누적 경험치 threshold(L) = (L-1)(10L+30).
코드트리 전체 커리큘럼(약 1,300장, 평균 15~20 XP)을 다 풀면 Lv 50 근처에 닿도록 맞췄다.
"""

from __future__ import annotations

from dataclasses import dataclass

# (도달 레벨, 단계 이름) — 캐릭터 모양이 바뀌는 지점
STAGES = [(1, "씨앗"), (3, "새싹"), (6, "묘목"), (10, "어린 나무"), (15, "나무"),
          (20, "큰 나무"), (28, "꽃나무"), (36, "열매 나무"), (45, "거목")]


def need(level: int) -> int:
    """레벨 level 에서 다음 레벨까지 필요한 경험치."""
    return 20 * level + 30


def threshold(level: int) -> int:
    """레벨 level 에 도달하는 누적 경험치."""
    return (level - 1) * (10 * level + 30)


@dataclass(frozen=True)
class LevelInfo:
    total: int          # 누적 경험치
    level: int
    xp: int             # 현재 레벨에서 쌓은 경험치
    need: int           # 다음 레벨까지 필요한 경험치(현재 레벨 구간 전체)
    stage: int          # 1~len(STAGES)
    stage_name: str
    next_stage_level: int | None  # 다음 단계가 열리는 레벨(마지막 단계면 None)

    @property
    def pct(self) -> float:
        return self.xp / self.need * 100 if self.need else 0.0

    @property
    def remaining(self) -> int:
        return self.need - self.xp


def level_for(total_xp: int) -> LevelInfo:
    total = max(0, int(total_xp))
    level = 1
    while threshold(level + 1) <= total:
        level += 1
    stage = max(i for i, (lv, _) in enumerate(STAGES) if lv <= level)
    nxt = STAGES[stage + 1][0] if stage + 1 < len(STAGES) else None
    return LevelInfo(total=total, level=level, xp=total - threshold(level), need=need(level),
                     stage=stage + 1, stage_name=STAGES[stage][1], next_stage_level=nxt)
