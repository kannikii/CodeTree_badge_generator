import unittest
import xml.dom.minidom
from datetime import date

from codetree_badge.curriculum import Curriculum, Trail
from codetree_badge.progress import compute
from codetree_badge.render import ROW_PITCH, fit, render, tw
from codetree_badge.solutions import SolutionData

from .helpers import lesson, small_curriculum
from .test_progress import solution


def curriculum_with_lessons(n: int, name: str = "자료구조 알고리즘") -> Curriculum:
    return Curriculum(trails=[Trail("novice-high", name, 3, [lesson(f"l{i}", [(f"c{i}", "Problem")]) for i in range(n)])])


def height(svg: str) -> int:
    return int(xml.dom.minidom.parseString(svg).documentElement.getAttribute("height"))


class RenderTest(unittest.TestCase):
    def test_valid_xml_both_themes(self):
        rep = compute(small_curriculum(), solution(["b1-i"], latest="b2-p1"), date(2026, 10, 30), "Asia/Seoul")
        for theme in ("light", "dark"):
            doc = xml.dom.minidom.parseString(render(rep, theme))
            self.assertEqual(doc.documentElement.getAttribute("width"), "560")
            self.assertTrue(doc.getElementsByTagName("title")[0].firstChild.data.startswith("코드트리 학습 현황"))

    def test_height_grows_by_rows_of_32(self):
        h = {n: height(render(compute(curriculum_with_lessons(n), SolutionData(), date(2026, 10, 30), "UTC")))
             for n in (29, 32, 33, 52, 87)}
        self.assertEqual(h[29], h[32])
        self.assertEqual(h[33] - h[32], ROW_PITCH)
        self.assertEqual(h[52], h[33])
        self.assertEqual(h[87] - h[52], ROW_PITCH)

    def test_one_hexagon_per_lesson(self):
        rep = compute(curriculum_with_lessons(52), SolutionData(), date(2026, 10, 30), "UTC")
        svg = render(rep)
        # 범례 1개 + 레슨 52개가 '시작하지 않음' 육각형
        self.assertEqual(svg.count('class="todo"'), 53)

    def test_text_is_escaped(self):
        rep = compute(curriculum_with_lessons(3, name="<트리 & 그래프>"), SolutionData(), date(2026, 10, 30), "UTC")
        svg = render(rep)
        xml.dom.minidom.parseString(svg)
        self.assertIn("&lt;트리 &amp; 그래프&gt;", svg)

    def test_chip_only_when_current(self):
        cur = small_curriculum()
        with_chip = render(compute(cur, solution(["b1-i", "b1-p1"], latest="b2-i"), date(2026, 10, 30), "Asia/Seoul"))
        without = render(compute(cur, solution(["b1-i", "b1-p1"], latest="a1-i"), date(2026, 10, 30), "Asia/Seoul"))
        self.assertIn("현재 학습 중", with_chip)
        self.assertNotIn("현재 학습 중", without)

    def test_footer_modes(self):
        cur = small_curriculum()
        auto = render(compute(cur, solution(["b1-i"]), date(2026, 10, 30), "Asia/Seoul"))
        fixed = render(compute(cur, solution(["b1-i"]), date(2026, 10, 30), "Asia/Seoul", "3"))
        self.assertIn("가장 많이 푼 트레일 기준 · 2026.10.30", auto)
        self.assertIn("Trail 3 고정 · 2026.10.30", fixed)
        empty = render(compute(cur, SolutionData(), date(2026, 10, 30), "Asia/Seoul"))
        self.assertIn("최근 통과 · 아직 없음", empty)

    def test_fit(self):
        long = "가" * 60
        out = fit(long, 12, 100)
        self.assertTrue(out.endswith("…"))
        self.assertLessEqual(tw(out, 12), 100)
        self.assertEqual(fit("짧음", 12, 100), "짧음")

    def test_deterministic(self):
        cur = small_curriculum()
        a = render(compute(cur, solution(["b1-i"], latest="b2-i"), date(2026, 10, 30), "Asia/Seoul"))
        b = render(compute(cur, solution(["b1-i"], latest="b2-i"), date(2026, 10, 30), "Asia/Seoul"))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
