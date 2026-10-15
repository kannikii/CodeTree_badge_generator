import contextlib
import io
import json
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

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
        for name in ("codetree-light.svg", "codetree-dark.svg"):
            xml.dom.minidom.parse(str(out / name))
        data = json.loads((out / "codetree.json").read_text(encoding="utf-8"))
        self.assertEqual(data["source"]["curriculum"], "sample")

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
        self.assertIn("코드트리 배지 갱신", summary.read_text(encoding="utf-8"))

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

    def test_bad_timezone(self):
        self.assertEqual(run("--sample", "--out", str(self.root / "o3"), "--tz", "Mars/Base"), 2)


if __name__ == "__main__":
    unittest.main()
