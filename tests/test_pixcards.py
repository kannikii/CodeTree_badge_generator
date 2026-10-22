import unittest
import xml.dom.minidom
from dataclasses import replace
from datetime import date

from codetree_badge import sample
from codetree_badge.levels import STAGES, level_for, threshold
from codetree_badge.pix import missing_glyphs, text_width
from codetree_badge.progress import compute
from codetree_badge.render_level import render_level, summary_text as level_summary
from codetree_badge.render_xp import render_xp, summary_text as xp_summary
from codetree_badge.solutions import SolutionData

from .helpers import small_curriculum


def size(svg: str) -> tuple[int, int]:
    el = xml.dom.minidom.parseString(svg).documentElement
    return int(el.getAttribute("width")), int(el.getAttribute("height"))


def title(svg: str) -> str:
    return xml.dom.minidom.parseString(svg).getElementsByTagName("title")[0].firstChild.data


class PixCardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cur, sol = sample.build(sample.SAMPLE_TODAY, "Asia/Seoul")
        cls.rep = compute(cur, sol, sample.SAMPLE_TODAY, "Asia/Seoul")
        cls.empty = compute(small_curriculum(), SolutionData(), date(2026, 10, 30), "Asia/Seoul")

    def with_total(self, total: int):
        return replace(self.rep, xp=replace(self.rep.xp, level=level_for(total)))

    def test_xp_card_both_themes(self):
        for theme in ("light", "dark"):
            svg = render_xp(self.rep, theme)
            self.assertEqual(size(svg), (560, 224))
            self.assertEqual(title(svg), "일일 경험치: 오늘 80/50 XP, 최근 14일 중 13일 목표 달성, 최고 110 XP, 누적 4180 XP")
            self.assertIn('shape-rendering="crispEdges"', svg)

    def test_level_card_both_themes(self):
        for theme in ("light", "dark"):
            svg = render_level(self.rep, theme)
            self.assertEqual(size(svg), (200, 272))
            self.assertEqual(title(svg), "성장 레벨: Lv.19 나무, 다음 레벨까지 190 XP, 누적 4180 XP, Lv.20 에 큰 나무")

    def test_cards_without_any_pass(self):
        xp = render_xp(self.empty)
        lv = render_level(self.empty)
        self.assertEqual(title(xp), "일일 경험치: 오늘 0/50 XP, 최근 14일 중 0일 목표 달성, 최고 0 XP, 누적 0 XP")
        self.assertTrue(title(lv).startswith("성장 레벨: Lv.1 씨앗, 다음 레벨까지 50 XP"))

    def test_level_card_for_every_stage_and_huge_levels(self):
        totals = [threshold(lv) for lv, _ in STAGES] + [threshold(lv) - 1 for lv, _ in STAGES[1:]] + [120_000, 999_999]
        for total in totals:
            svg = render_level(self.with_total(total))
            self.assertEqual(size(svg), (200, 272), total)
            self.assertIn(f"누적 {total} XP", title(svg))

    def test_last_stage_summary_has_no_next_stage(self):
        self.assertEqual(level_summary(level_for(21120)), "성장 레벨: Lv.45 거목, 다음 레벨까지 930 XP, 누적 21120 XP")

    def test_summary_text_matches_stats(self):
        x = self.rep.xp
        self.assertEqual((x.goal, x.today, x.total, x.goal_days, x.best, len(x.days)), (50, 80, 4180, 13, 110, 14))
        self.assertEqual(xp_summary(x), title(render_xp(self.rep)))
        self.assertEqual(level_summary(x.level), title(render_level(self.rep)))

    def test_deterministic_and_theme_differs(self):
        self.assertEqual(render_xp(self.rep, "dark"), render_xp(self.rep, "dark"))
        self.assertEqual(render_level(self.rep, "light"), render_level(self.rep, "light"))
        self.assertNotEqual(render_xp(self.rep, "light"), render_xp(self.rep, "dark"))
        self.assertNotEqual(render_level(self.rep, "light"), render_level(self.rep, "dark"))

    def test_pixel_font_covers_every_drawn_string(self):
        for s in ("일일 경험치", "성장 레벨", "Lv.", "목표 50 XP · 최근 14일", "오늘", "0123456789"):
            self.assertEqual(missing_glyphs(s, "g9"), "", s)
            self.assertEqual(missing_glyphs(s, "g7"), "", s)
        for _, name in STAGES:
            self.assertEqual(missing_glyphs(name, "g7"), "", name)
        for s in ("123 / 456 XP 달성!", "누적 4180 XP", "목표 달성 13/14일", "56%"):
            self.assertEqual(missing_glyphs(s, "g7"), "", s)
        self.assertEqual(missing_glyphs("0123456789", "g11b"), "")
        self.assertGreater(text_width("Lv.", "g9", 2), 0)


if __name__ == "__main__":
    unittest.main()
