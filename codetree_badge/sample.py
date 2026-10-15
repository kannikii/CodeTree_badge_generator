"""--sample 용 합성 데이터. 네트워크·git 없이 배지 모양을 확인할 때 쓴다(실제 사용자 데이터 아님)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .curriculum import Card, Curriculum, Lesson, Trail
from .solutions import CardRecord, PassEvent, SolutionData

SAMPLE_TODAY = date(2026, 10, 15)

_TRAILS = [  # (alias, 이름, 레슨 수) — 레슨 수는 코드트리 트레일 규모와 비슷하게 맞춤
    ("novice-low", "프로그래밍 기초", 87),
    ("novice-mid", "프로그래밍 연습", 29),
    ("novice-high", "자료구조 알고리즘", 52),
    ("intermediate-low", "알고리즘 입문", 19),
    ("intermediate-mid", "알고리즘 기본", 18),
    ("intermediate-high", "알고리즘 실전", 17),
]
_CARD_TYPES = ["Introduction", "Problem", "Problem", "Problem", "Test"]

# 트레일별 레슨 상태 (# 완료 · o 테스트만 통과 · O 일부 통과 · B 일부 통과 + 가장 최근 학습 · . 없음)
_PATTERNS = {
    1: "#####" "####O",
    2: "#####" "#o##O" "##",
    3: "##o##" "#####" "####O" "#####" "#o##B",
}
# 최근 28일 학습 여부(왼쪽=과거, 오른쪽=오늘) + 그 이전 학습일 수
_RECENT_DAYS = "···■■■■■·■■■■■■■■■■·■■■■■■■■"
_OLDER_DAYS = 19


def build(today: date = SAMPLE_TODAY, tz: str = "Asia/Seoul") -> tuple[Curriculum, SolutionData]:
    trails = []
    for order, (alias, name, n) in enumerate(_TRAILS, start=1):
        lessons = [Lesson(alias=f"{alias}-lesson-{i + 1}", name=f"샘플 레슨 {i + 1}", chapter=f"챕터 {i // 5 + 1}",
                          cards=[Card(alias=f"{alias}-{i + 1}-{k}", type=ty) for k, ty in enumerate(_CARD_TYPES)])
                   for i in range(n)]
        trails.append(Trail(alias=alias, name=name, order=order, lessons=lessons))
    cur = Curriculum(trails=trails)

    passed: list[tuple[Trail, Lesson, Card]] = []
    latest: tuple[Trail, Lesson, Card] | None = None
    for trail in trails:
        for i, mark in enumerate(_PATTERNS.get(trail.order, "")):
            lesson = trail.lessons[i]
            cards = lesson.cards
            picked = {"#": cards, "o": [cards[-1]], "O": [cards[1]], "B": cards[:2]}.get(mark, [])
            passed.extend((trail, lesson, c) for c in picked)
            if mark == "B":
                latest = (trail, lesson, cards[1])

    zone = ZoneInfo(tz)
    days = [today - timedelta(days=k) for k, ch in enumerate(reversed(_RECENT_DAYS)) if ch == "■"]
    days += [today - timedelta(days=40 + 2 * k) for k in range(_OLDER_DAYS)]
    days.sort()

    sol = SolutionData()
    ordered = [p for p in passed if latest is None or p[2] != latest[2]] + ([latest] if latest else [])
    for n, (trail, lesson, card) in enumerate(ordered):
        is_latest = latest is not None and card == latest[2]
        day = today if is_latest else days[min(len(days) - 1, n * len(days) // max(1, len(ordered)))]
        when = datetime.combine(day, time(23 if is_latest else 20, 0), tzinfo=zone) + timedelta(seconds=n)
        title = f"샘플 문제 {lesson.name[-2:].strip()}-{card.alias.rsplit('-', 1)[1]}"
        sol.cards[card.alias] = CardRecord(alias=card.alias, title=title, tag="챌린지",
                                           path_label=f"Trail {trail.order} / {lesson.chapter} / {lesson.name}")
        sol.first_passed[card.alias] = when
        sol.events.append(PassEvent(when=when, sha=f"{n:040x}", title=title, alias=card.alias))
    # 학습일이 카드 수보다 많으면 남는 날에도 이벤트를 하나씩 둔다(스트릭 모양 유지)
    used = {e.when.date() for e in sol.events}
    for day in days:
        if day not in used:
            sol.events.append(PassEvent(when=datetime.combine(day, time(9, 0), tzinfo=zone), sha="0" * 40,
                                        title="샘플 문제", alias=None))
    sol.events.sort(key=lambda e: e.when, reverse=True)
    return cur, sol
