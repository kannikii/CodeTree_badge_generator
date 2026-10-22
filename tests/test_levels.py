import unittest

from codetree_badge.levels import STAGES, level_for, need, threshold


class LevelFormulaTest(unittest.TestCase):
    def test_need_and_threshold(self):
        self.assertEqual((need(1), need(2), need(10)), (50, 70, 230))
        self.assertEqual(threshold(1), 0)
        for lv in range(1, 120):
            self.assertEqual(threshold(lv + 1) - threshold(lv), need(lv))

    def test_level_boundaries(self):
        for lv in range(2, 120):
            self.assertEqual(level_for(threshold(lv)).level, lv)
            self.assertEqual(level_for(threshold(lv) - 1).level, lv - 1)

    def test_known_values(self):
        cases = {
            0: (1, 0, 50, "씨앗"), 49: (1, 49, 50, "씨앗"), 50: (2, 0, 70, "씨앗"),
            120: (3, 0, 90, "새싹"), 2340: (14, 130, 310, "어린 나무"),
            4180: (19, 220, 410, "나무"), 21120: (45, 0, 930, "거목"),
        }
        for total, (level, xp, nd, name) in cases.items():
            info = level_for(total)
            self.assertEqual((info.level, info.xp, info.need, info.stage_name), (level, xp, nd, name), total)
            self.assertEqual(info.total, total)
            self.assertEqual(info.remaining, nd - xp)

    def test_stage_thresholds(self):
        self.assertEqual([threshold(lv) for lv, _ in STAGES], [0, 120, 450, 1170, 2520, 4370, 8370, 13650, 21120])
        for i, (lv, name) in enumerate(STAGES):
            info = level_for(threshold(lv))
            self.assertEqual((info.stage, info.stage_name), (i + 1, name))
            if i:
                self.assertEqual(level_for(threshold(lv) - 1).stage, i)   # 바로 전 XP 는 이전 단계
        self.assertEqual(level_for(0).next_stage_level, 3)
        self.assertEqual(level_for(4180).next_stage_level, 20)
        self.assertIsNone(level_for(21120).next_stage_level)
        self.assertEqual(level_for(999_999).stage_name, "거목")

    def test_negative_and_pct(self):
        self.assertEqual(level_for(-5).total, 0)
        info = level_for(25)
        self.assertEqual((info.pct, info.remaining), (50.0, 25))


if __name__ == "__main__":
    unittest.main()
