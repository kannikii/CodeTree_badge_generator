import unittest
from datetime import date, datetime, timedelta, timezone

from codetree_badge.curriculum import Card, normalize
from codetree_badge.progress import compute, compute_streak, lesson_state, pick_display, to_json, trail_view
from codetree_badge.solutions import CardRecord, PassEvent, SolutionData

from .helpers import small_curriculum

KST = timezone(timedelta(hours=9))


def solution(aliases, latest=None, days=()):
    """aliases 를 통과한 SolutionData. latest 가 있으면 그 카드가 가장 최근 통과."""
    sol = SolutionData()
    base = datetime(2026, 10, 1, 12, tzinfo=KST)
    for i, a in enumerate(aliases):
        sol.cards[a] = CardRecord(alias=a, title=f"제목 {a}", path_label="Trail 2 / 챕터 / 레슨")
        sol.events.append(PassEvent(when=base + timedelta(minutes=i), sha="0" * 40, title=f"제목 {a}", alias=a))
    for d in days:
        sol.events.append(PassEvent(when=datetime(d.year, d.month, d.day, 9, tzinfo=KST), sha="1" * 40, title="x", alias=None))
    if latest:
        sol.cards.setdefault(latest, CardRecord(alias=latest, title=f"제목 {latest}"))
        sol.events.append(PassEvent(when=datetime(2026, 10, 30, tzinfo=KST), sha="2" * 40, title=f"제목 {latest}", alias=latest))
    sol.events.sort(key=lambda e: e.when, reverse=True)
    return sol


class LessonStateTest(unittest.TestCase):
    cards = [Card("i", "Introduction"), Card("p1", "Problem"), Card("p2", "Problem"), Card("t", "Test")]

    def test_rules(self):
        self.assertEqual(lesson_state(self.cards, {"i", "p1", "p2", "t"}), "#")
        self.assertEqual(lesson_state(self.cards, {"t"}), "o")
        self.assertEqual(lesson_state(self.cards, {"i", "t"}), "o")
        self.assertEqual(lesson_state(self.cards, {"p1"}), "O")
        self.assertEqual(lesson_state(self.cards, set()), ".")

    def test_lesson_without_test_card(self):
        cards = [Card("i", "Introduction"), Card("p", "Problem")]
        self.assertEqual(lesson_state(cards, {"i"}), "O")
        self.assertEqual(lesson_state(cards, {"i", "p"}), "#")
        self.assertEqual(lesson_state([], {"x"}), ".")


class NormalizeTest(unittest.TestCase):
    def test_sorting_and_chapter_without_lessons(self):
        raw = [
            {"name": "B", "alias": "novice-mid", "order": 2, "chapters": [
                {"name": "둘째", "alias": "c2", "order": 2, "lessons": [
                    {"name": "L2", "alias": "l2", "order": 2, "curated_cards": [{"alias": "y", "type": "Test", "order": 1}]},
                    {"name": "L1", "alias": "l1", "order": 1, "curated_cards": [
                        {"alias": "x2", "type": "Problem", "order": 2}, {"alias": "x1", "type": "Introduction", "order": 1}]}]},
                {"name": "첫째", "alias": "c1", "order": 1, "curated_cards": [{"alias": "w", "type": "Problem", "order": 1}]},
            ]},
            {"name": "A", "alias": "novice-low", "order": 1, "chapters": []},
        ]
        cur = normalize(raw)
        self.assertEqual([t.alias for t in cur.trails], ["novice-low", "novice-mid"])
        mid = cur.trails[1]
        self.assertEqual([ls.name for ls in mid.lessons], ["첫째", "L1", "L2"])  # 챕터 직속 카드는 레슨 1개
        self.assertEqual([c.alias for c in mid.lessons[1].cards], ["x1", "x2"])
        self.assertEqual(mid.level, "Novice Mid")

    def test_rejects_unexpected_shape(self):
        with self.assertRaises(Exception):
            normalize({"detail": "error"})


class PickDisplayTest(unittest.TestCase):
    def setUp(self):
        self.cur = small_curriculum()

    def views(self, passed):
        return [trail_view(t, passed) for t in self.cur.trails if t.order >= 1]

    def test_most_passed_wins(self):
        passed = {"a1-i", "a1-p1", "a2-i", "b1-i", "b1-p1", "b1-p2", "b2-i"}
        t, mode, _ = pick_display(self.views(passed))
        self.assertEqual((t.no, mode), (2, "auto"))

    def test_tie_uses_ratio_then_number(self):
        # Trail 1(8장) 2개 vs Trail 3(4장) 2개 → 비율이 높은 Trail 3
        t, _, _ = pick_display(self.views({"a1-i", "a1-p1", "c1-i", "c1-p1"}))
        self.assertEqual(t.no, 3)

    def test_no_progress_shows_first_trail(self):
        t, _, _ = pick_display(self.views(set()))
        self.assertEqual(t.no, 1)

    def test_fixed_and_invalid_choice(self):
        t, mode, w = pick_display(self.views(set()), "2")
        self.assertEqual((t.no, mode, w), (2, "fixed", []))
        t, mode, w = pick_display(self.views(set()), "9")
        self.assertEqual((t.no, mode), (1, "auto"))
        self.assertTrue(w)


class ComputeTest(unittest.TestCase):
    def setUp(self):
        self.cur = small_curriculum()

    def test_overall_excludes_trail0_and_counts(self):
        rep = compute(self.cur, solution(["z1-i", "b1-i"]), date(2026, 10, 30), "Asia/Seoul")
        self.assertEqual((rep.passed, rep.total), (1, 24))
        self.assertEqual([t.no for t in rep.trails], [1, 2, 3])

    def test_current_lesson_marked_in_display_trail(self):
        sol = solution(["b1-i", "b1-p1", "b1-p2", "b1-t", "b2-i"], latest="b2-p1")
        rep = compute(self.cur, sol, date(2026, 10, 30), "Asia/Seoul")
        self.assertEqual(rep.display.no, 2)
        self.assertEqual(rep.display.pattern, "#B.")
        self.assertTrue(rep.is_current)
        self.assertEqual((rep.recent.trail_no, rep.recent.lesson), (2, "b2"))

    def test_completed_lesson_is_not_marked_current(self):
        sol = solution(["b1-i", "b1-p1", "b1-p2"], latest="b1-t")
        rep = compute(self.cur, sol, date(2026, 10, 30), "Asia/Seoul")
        self.assertEqual(rep.display.pattern, "#..")

    def test_latest_in_other_trail(self):
        sol = solution(["b1-i", "b1-p1", "b2-i"], latest="a1-i")
        rep = compute(self.cur, sol, date(2026, 10, 30), "Asia/Seoul")
        self.assertEqual(rep.display.no, 2)
        self.assertFalse(rep.is_current)
        self.assertNotIn("B", rep.display.pattern)

    def test_unknown_alias_is_warned_not_counted(self):
        rep = compute(self.cur, solution(["b1-i", "gone-card"]), date(2026, 10, 30), "Asia/Seoul")
        self.assertEqual(rep.unknown_aliases, ["gone-card"])
        self.assertEqual(rep.passed, 1)
        self.assertTrue(any("gone-card" in w for w in rep.warnings))

    def test_trail0_card_missing_from_curriculum_is_silent(self):
        # 공개 커리큘럼에는 Trail 0(코드트리 입문)이 없다 → 경고 없이 제외하고, 최근 통과 표시는 README 경로로 채운다
        sol = solution(["b1-i"])
        sol.cards["nl-pre-output"] = CardRecord(alias="nl-pre-output", title="출력 입문",
                                                path_label="Trail 0 / 기본 / 출력 입문")
        sol.events.insert(0, PassEvent(when=datetime(2026, 10, 30, tzinfo=KST), sha="3" * 40,
                                       title="출력 입문", alias="nl-pre-output"))
        rep = compute(self.cur, sol, date(2026, 10, 30), "Asia/Seoul")
        self.assertEqual(rep.warnings, [])
        self.assertEqual(rep.unknown_aliases, ["nl-pre-output"])
        self.assertEqual((rep.recent.trail_no, rep.recent.lesson), (0, "출력 입문"))
        self.assertFalse(rep.is_current)

    def test_json_has_no_clock_time(self):
        rep = compute(self.cur, solution(["b1-i"]), date(2026, 10, 30), "Asia/Seoul")
        data = to_json(rep, "me/PS", "live")
        self.assertEqual(data["date"], "2026-10-30")
        self.assertEqual(data["source"]["repo"], "me/PS")
        self.assertEqual(data["display"]["lessons"], "B..")  # 유일한 통과가 곧 최근 학습 레슨
        self.assertNotIn("T", data["date"])


class StreakTest(unittest.TestCase):
    def days(self, *mmdd):
        return {date(2026, m, d) for m, d in mmdd}

    def test_current_counts_today_or_yesterday(self):
        ds = self.days((10, 11), (10, 12), (10, 13))
        self.assertEqual(compute_streak(ds, date(2026, 10, 13)).current, 3)
        self.assertEqual(compute_streak(ds, date(2026, 10, 14)).current, 3)  # 오늘 아직 안 했어도 어제까지 이어짐
        self.assertEqual(compute_streak(ds, date(2026, 10, 15)).current, 0)

    def test_best_total_and_month_boundary(self):
        ds = self.days((9, 29), (9, 30), (10, 1), (10, 2), (10, 5), (10, 6))
        st = compute_streak(ds, date(2026, 10, 20))
        self.assertEqual((st.best, st.total, st.current), (4, 6, 0))
        self.assertEqual((st.first, st.last), (date(2026, 9, 29), date(2026, 10, 6)))

    def test_strip_and_future_dates(self):
        ds = self.days((10, 14), (10, 15), (10, 16))
        st = compute_streak(ds, date(2026, 10, 15))
        self.assertEqual(len(st.strip), 28)
        self.assertEqual(st.strip[-2:], [True, True])   # 맨 오른쪽이 오늘
        self.assertEqual((st.total, st.current), (2, 2))  # 미래 날짜는 무시

    def test_empty(self):
        st = compute_streak(set(), date(2026, 10, 15))
        self.assertEqual((st.current, st.best, st.total, st.first), (0, 0, 0, None))


if __name__ == "__main__":
    unittest.main()
