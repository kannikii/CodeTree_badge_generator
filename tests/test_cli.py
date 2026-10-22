import contextlib
import io
import json
import os
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path
from unittest import mock

from codetree_badge.__main__ import main
from codetree_badge.curriculum import to_cache

from .helpers import make_repo, readme, small_curriculum


def run(*args) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return main(list(args))


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sample_mode(self):
        out = self.root / "preview"
        self.assertEqual(run("--sample", "--out", str(out)), 0)
        for kind in ("", "-xp", "-level"):
            for theme in ("light", "dark"):
                xml.dom.minidom.parse(str(out / f"codetree{kind}-{theme}.svg"))
        data = json.loads((out / "codetree.json").read_text(encoding="utf-8"))
        self.assertEqual(data["source"]["curriculum"], "sample")
        self.assertEqual((data["xp"]["goal"], data["xp"]["today"], data["xp"]["total"]), (50, 80, 4180))
        self.assertEqual((data["level"]["level"], data["level"]["stage_name"]), (19, "나무"))

    def test_offline_with_cache(self):
        repo = make_repo(self.root / "ps", [
            {"message": "[Passed] B1 개념", "when": "2026-10-07T21:00:00+09:00",
             "files": {"trail2/B1 개념/README.md": readme("b1-i", "B1 개념", "개념")}},
            {"message": "[Passed] B1 문제 (1ms, 0MB)", "when": "2026-10-08T21:00:00+09:00",
             "files": {"trail2/B1 문제/README.md": readme("b1-p1", "B1 문제"), "trail2/B1 문제/s.py": "print(1)"}},
        ])
        out = self.root / "out"
        out.mkdir()
        (out / "curriculum-cache.json").write_text(json.dumps(to_cache(small_curriculum()), ensure_ascii=False),
                                                  encoding="utf-8")
        summary = self.root / "summary.md"
        code = run("--solutions", str(repo), "--out", str(out), "--offline", "--today", "2026-10-08",
                   "--source-repo", "me/PS", "--summary-file", str(summary))
        self.assertEqual(code, 0)
        data = json.loads((out / "codetree.json").read_text(encoding="utf-8"))
        self.assertEqual(data["display"]["trail"], 2)
        self.assertEqual(data["display"]["lessons"], "B..")
        self.assertEqual(data["streak"]["current"], 2)
        self.assertEqual(data["recent"]["title"], "B1 문제")
        self.assertEqual(data["source"], {"repo": "me/PS", "curriculum": "cache"})
        self.assertEqual((data["xp"]["today"], data["xp"]["total"], data["xp"]["goal_days"]), (10, 20, 0))
        self.assertEqual(data["level"]["level"], 1)
        text = summary.read_text(encoding="utf-8")
        self.assertIn("코드트리 배지 갱신", text)
        self.assertIn("| 일일 경험치 | 오늘 10/50 XP · 최근 14일 중 0일 목표 달성 |", text)
        self.assertIn("| 성장 레벨 | Lv.1 씨앗 (20/50 XP, 누적 20 XP) |", text)
        names = {p.name for p in out.iterdir()}
        self.assertTrue({f"codetree{k}-{t}.svg" for k in ("", "-xp", "-level") for t in ("light", "dark")} <= names)

        # 같은 입력이면 출력 파일이 바이트 단위로 같아야 한다(변경 없음 판정)
        before = {p.name: p.read_bytes() for p in out.iterdir()}
        self.assertEqual(run("--solutions", str(repo), "--out", str(out), "--offline", "--today", "2026-10-08",
                             "--source-repo", "me/PS"), 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()})

    def test_missing_solutions(self):
        self.assertEqual(run("--out", str(self.root / "o")), 2)

    def test_offline_without_cache_fails(self):
        repo = make_repo(self.root / "ps2", [{"message": "init", "when": "2026-10-01T00:00:00+09:00",
                                              "files": {"a.txt": "a"}}])
        self.assertEqual(run("--solutions", str(repo), "--out", str(self.root / "o2"), "--offline"), 1)

    def test_daily_goal_from_flag_and_env(self):
        out = self.root / "goal"
        self.assertEqual(run("--sample", "--out", str(out), "--daily-goal", "90"), 0)
        data = json.loads((out / "codetree.json").read_text(encoding="utf-8"))
        self.assertEqual(data["xp"]["goal"], 90)
        self.assertEqual(data["xp"]["goal_days"], sum(1 for d in data["xp"]["days"] if d["xp"] >= 90))
        with mock.patch.dict(os.environ, {"BADGE_DAILY_GOAL": " 140 "}):
            self.assertEqual(run("--sample", "--out", str(out)), 0)
        data = json.loads((out / "codetree.json").read_text(encoding="utf-8"))
        self.assertEqual(data["xp"]["goal"], 140)

    def test_bad_daily_goal(self):
        out = str(self.root / "bad")
        for bad in ("0", "-5", "abc", "1.5", ""):
            self.assertEqual(run("--sample", "--out", out, "--daily-goal", bad), 2, repr(bad))
        with mock.patch.dict(os.environ, {"BADGE_DAILY_GOAL": "many"}):
            self.assertEqual(run("--sample", "--out", out), 2)

    def test_bad_timezone(self):
        self.assertEqual(run("--sample", "--out", str(self.root / "o3"), "--tz", "Mars/Base"), 2)


if __name__ == "__main__":
    unittest.main()
