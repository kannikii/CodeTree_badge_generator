"""통과 카드 + 커리큘럼 → 레슨 상태, 표시 트레일, 스트릭."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .curriculum import Card, Curriculum, Trail
from .solutions import SolutionData

# 레슨 상태 기호
DONE, TEST_DONE, STARTED, TODO, CURRENT = "#", "o", "O", ".", "B"
STRIP_DAYS = 28


@dataclass
class LessonView:
    name: str
    chapter: str
    passed: int
    total: int
    state: str


@dataclass
class TrailView:
    no: int
    alias: str
    level: str
    name: str
    passed: int
    total: int
    lessons: list[LessonView]

    @property
    def pct(self) -> float:
        return self.passed / self.total * 100 if self.total else 0.0

    @property
    def pattern(self) -> str:
        return "".join(ls.state for ls in self.lessons)


@dataclass
class Streak:
    current: int
    best: int
    total: int
    first: date | None
    last: date | None
    strip: list[bool]  # 왼쪽=과거 … 오른쪽=오늘


@dataclass
class Recent:
    title: str
    alias: str | None
    when: datetime
    day: date                 # 설정 타임존 기준 날짜
    trail_no: int | None
    lesson: str


@dataclass
class Report:
    trails: list[TrailView]
    display: TrailView
    mode: str                 # "auto" | "fixed"
    passed: int
    total: int
    streak: Streak
    recent: Recent | None
    is_current: bool          # 표시 트레일 == 최근 학습 트레일
    today: date
    tz: str
    unknown_aliases: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def pct(self) -> float:
        return self.passed / self.total * 100 if self.total else 0.0


def lesson_state(cards: list[Card], passed: set[str]) -> str:
    if not cards:
        return TODO
    hits = [c.alias in passed for c in cards]
    if all(hits):
        return DONE
    tests = [c for c in cards if c.type == "Test"]
    if tests and all(c.alias in passed for c in tests):
        return TEST_DONE
    return STARTED if any(hits) else TODO


def trail_view(trail: Trail, passed: set[str]) -> TrailView:
    lessons = [LessonView(name=ls.name, chapter=ls.chapter,
                          passed=sum(1 for c in ls.cards if c.alias in passed), total=len(ls.cards),
                          state=lesson_state(ls.cards, passed))
               for ls in trail.lessons]
    return TrailView(no=trail.order, alias=trail.alias, level=trail.level, name=trail.name,
                     passed=sum(ls.passed for ls in lessons), total=sum(ls.total for ls in lessons),
                     lessons=lessons)


def pick_display(trails: list[TrailView], choice: str = "auto") -> tuple[TrailView, str, list[str]]:
    """가장 많이 푼 트레일(동률이면 완료율 → 번호 큰 쪽). 통과가 없으면 가장 앞 트레일."""
    warnings = []
    choice = (choice or "auto").strip().lower()
    if choice not in ("", "auto"):
        for t in trails:
            if str(t.no) == choice or t.alias == choice:
                return t, "fixed", warnings
        warnings.append(f"BADGE_TRAIL={choice} 에 해당하는 트레일이 없어 자동 선택을 쓴다")
    if all(t.passed == 0 for t in trails):
        return min(trails, key=lambda t: t.no), "auto", warnings
    return max(trails, key=lambda t: (t.passed, t.pct, t.no)), "auto", warnings


def compute_streak(dates: set[date], today: date, days: int = STRIP_DAYS) -> Streak:
    past = sorted(d for d in dates if d <= today)
    best = run = 0
    prev = None
    for d in past:
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d
    have = set(past)
    current = 0
    cursor = today if today in have else today - timedelta(days=1)
    while cursor in have:
        current += 1
        cursor -= timedelta(days=1)
    strip = [(today - timedelta(days=k)) in have for k in range(days - 1, -1, -1)]
    return Streak(current=current, best=best, total=len(past),
                  first=past[0] if past else None, last=past[-1] if past else None, strip=strip)


def compute(cur: Curriculum, sol: SolutionData, today: date, tz: str, trail_choice: str = "auto") -> Report:
    index = cur.card_index()
    passed = {a for a in sol.cards if a in index}
    unknown = sorted(a for a in sol.cards if a not in index)

    # 표시 대상은 Trail 1 이상(order >= 1). codetree-101(order 0)은 학습 현황 화면처럼 제외한다.
    views = [trail_view(t, passed) for t in sorted(cur.trails, key=lambda t: t.order) if t.order >= 1]
    if not views:
        raise ValueError("커리큘럼에 Trail 1 이상의 트레일이 없다")
    display, mode, warnings = pick_display(views, trail_choice)

    recent = None
    latest = sol.latest
    if latest is not None:
        trail_no, lesson_name = None, ""
        if latest.alias and latest.alias in index:
            trail, li, _ = index[latest.alias]
            trail_no, lesson_name = trail.order, trail.lessons[li].name
            if trail.order == display.no and display.lessons[li].state != DONE:
                display.lessons[li].state = CURRENT
        elif latest.alias and latest.alias in sol.cards:  # 커리큘럼에 없는 카드(예: Trail 0)는 README 경로로 보완
            trail_no, lesson_name = sol.cards[latest.alias].trail_no, sol.cards[latest.alias].lesson_label
        recent = Recent(title=latest.title, alias=latest.alias, when=latest.when,
                        day=latest.when.astimezone(ZoneInfo(tz)).date(), trail_no=trail_no, lesson=lesson_name)

    # Trail 0(코드트리 입문)은 공개 커리큘럼에 없고 원래 집계 대상도 아니므로 경고하지 않는다.
    missing = [a for a in unknown if sol.cards[a].trail_no != 0]
    if missing:
        warnings.append(f"커리큘럼에 없는 카드 {len(missing)}개는 제외했다: {', '.join(missing[:5])}"
                        + (" …" if len(missing) > 5 else ""))

    return Report(trails=views, display=display, mode=mode,
                  passed=sum(v.passed for v in views), total=sum(v.total for v in views),
                  streak=compute_streak(sol.study_dates(tz), today), recent=recent,
                  is_current=bool(recent and recent.trail_no == display.no),
                  today=today, tz=tz, unknown_aliases=unknown, warnings=warnings)


def to_json(report: Report, source_repo: str = "", curriculum_source: str = "") -> dict:
    """codetree.json 내용. 실행 시각 대신 날짜만 넣어 같은 날 같은 데이터면 내용이 같다."""
    d = report.display
    s = report.streak
    r = report.recent
    return {
        "schema": 1,
        "date": report.today.isoformat(),
        "timezone": report.tz,
        "source": {"repo": source_repo, "curriculum": curriculum_source},
        "overall": {"passed": report.passed, "total": report.total, "pct": round(report.pct, 1)},
        "display": {"trail": d.no, "alias": d.alias, "level": d.level, "name": d.name, "mode": report.mode,
                    "passed": d.passed, "total": d.total, "pct": round(d.pct, 1),
                    "is_current": report.is_current, "lessons": d.pattern},
        "trails": [{"trail": t.no, "alias": t.alias, "level": t.level, "name": t.name,
                    "passed": t.passed, "total": t.total, "pct": round(t.pct, 1), "lessons": len(t.lessons)}
                   for t in report.trails],
        "streak": {"current": s.current, "best": s.best, "total": s.total,
                   "first": s.first.isoformat() if s.first else None,
                   "last": s.last.isoformat() if s.last else None,
                   "recent_28": "".join("1" if x else "0" for x in s.strip)},
        "recent": None if r is None else {"title": r.title, "alias": r.alias, "trail": r.trail_no,
                                          "lesson": r.lesson, "date": r.day.isoformat()},
        "warnings": report.warnings,
    }
