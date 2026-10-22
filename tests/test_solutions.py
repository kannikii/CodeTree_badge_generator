import tempfile
import unittest
from datetime import date
from pathlib import Path

from codetree_badge.solutions import parse_readme, scan, title_from_subject

from .helpers import make_repo, readme


class ParseReadmeTest(unittest.TestCase):
    def test_basic(self):
        rec = parse_readme(readme("challenge-come-back", "되돌아오기"))
        self.assertEqual(rec.alias, "challenge-come-back")
        self.assertEqual(rec.title, "되돌아오기")
        self.assertEqual(rec.tag, "챌린지")
        self.assertEqual(rec.path_label, "Trail 2 / 시뮬레이션 II / dx dy technique")
        self.assertEqual(rec.lesson_label, "dx dy technique")

    def test_title_with_brackets(self):
        text = "# [[챌린지][특별] 문제 (2)](https://www.codetree.ai/trails/complete/curated-cards/x-y)\n"
        rec = parse_readme(text)
        self.assertEqual((rec.alias, rec.title, rec.tag), ("x-y", "[특별] 문제 (2)", "챌린지"))

    def test_chapter_with_slash_keeps_last_part_as_lesson(self):
        rec = parse_readme(readme("a", "A", path="Trail 3 / 배열, 연결 리스트 / 단일 연결 리스트"))
        self.assertEqual(rec.lesson_label, "단일 연결 리스트")

    def test_non_codetree_readme(self):
        self.assertIsNone(parse_readme("# [Silver III] 문제 - 1000\n\n[문제 링크](https://www.acmicpc.net/problem/1000)\n"))
        self.assertIsNone(parse_readme(""))

    def test_xp_row(self):
        self.assertEqual(parse_readme(readme("a", "A")).xp, 10)
        self.assertEqual(parse_readme(readme("a", "A", xp=35)).xp, 35)
        no_xp = "\n".join(ln for ln in readme("a", "A").splitlines() if "경험치" not in ln)
        self.assertEqual(parse_readme(no_xp).xp, 0)

    def test_title_from_subject(self):
        self.assertEqual(title_from_subject("[Passed] 되돌아오기 (2ms, 0MB)"), "되돌아오기")
        self.assertEqual(title_from_subject("[Passed] 출력결과 65"), "출력결과 65")
        self.assertEqual(title_from_subject("[Passed] 함수 f(x) 구하기 (2ms, 0MB)"), "함수 f(x) 구하기")


class ScanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.repo = make_repo(Path(cls.tmp.name) / "ps", [
            {"message": "[Passed] 되돌아오기 (1ms, 0MB)", "when": "2026-10-01T10:00:00+09:00",
             "files": {"trail2/되돌아오기/README.md": readme("a", "되돌아오기"), "trail2/되돌아오기/a.cpp": "int main(){}"}},
            {"message": "[Silver III] Title: 수 정렬하기, Time: 100 ms", "when": "2026-10-01T23:30:00+00:00",
             "files": {"백준/Silver/2750/README.md": "# [Silver III] 수 정렬하기 - 2750\n"}},
            {"message": "[Passed] 단일 연결 리스트 만들기", "when": "2026-10-02T21:00:00+09:00",
             "files": {"trail3/단일 연결 리스트 만들기/README.md": readme("b", "단일 연결 리스트 만들기", "개념",
                                                                     "Trail 3 / 배열, 연결 리스트 / 단일 연결 리스트")}},
            # 같은 카드 재통과: README 변경 없이 코드만 바뀐다
            {"message": "[Passed] 되돌아오기 (2ms, 0MB)", "when": "2026-10-03T09:00:00+09:00",
             "files": {"trail2/되돌아오기/a.cpp": "int main(){return 0;}"}},
            # 제목이 같은 서로 다른 카드가 같은 폴더를 덮어쓴다
            {"message": "[Passed] 같은 제목 (1ms, 0MB)", "when": "2026-10-05T09:00:00+09:00",
             "files": {"trail2/같은 제목/README.md": readme("s1", "같은 제목")}},
            {"message": "[Passed] 같은 제목 (1ms, 0MB)", "when": "2026-10-06T09:00:00+09:00",
             "files": {"trail2/같은 제목/README.md": readme("s2", "같은 제목")}},
            # 직접 메모를 단 커밋(README 수정, [Passed] 아님)은 학습일이 아니다
            {"message": "메모 추가", "when": "2026-10-07T09:00:00+09:00",
             "files": {"trail3/단일 연결 리스트 만들기/README.md":
                       readme("b", "단일 연결 리스트 만들기", "개념", "Trail 3 / 배열, 연결 리스트 / 단일 연결 리스트") + "\n메모\n"}},
            # 메시지 형식이 달라도 카드 README 가 새로 생기면 통과로 본다
            {"message": "Upload card", "when": "2026-10-09T16:30:00+00:00",
             "files": {"trail3/새 카드/README.md": readme("c", "새 카드", path="Trail 3 / 트리 / 트리")}},
            {"message": "루트 파일 수정", "when": "2026-10-11T09:00:00+09:00", "files": {"sort.cpp": "//"}},
        ])
        cls.data = scan(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_cards_include_collided_titles(self):
        self.assertEqual(set(self.data.cards), {"a", "b", "s1", "s2", "c"})

    def test_events_are_codetree_only_newest_first(self):
        self.assertEqual(len(self.data.events), 6)
        self.assertEqual(self.data.latest.alias, "c")
        self.assertEqual(self.data.latest.title, "새 카드")
        whens = [e.when for e in self.data.events]
        self.assertEqual(whens, sorted(whens, reverse=True))

    def test_repass_event_resolves_alias_from_folder_readme(self):
        repass = [e for e in self.data.events if e.when.day == 3]
        self.assertEqual(repass[0].alias, "a")

    def test_first_passed_keeps_earliest(self):
        self.assertEqual(self.data.first_passed["a"].isoformat(), "2026-10-01T10:00:00+09:00")

    def test_xp_counts_each_card_once(self):
        self.assertEqual({a: c.xp for a, c in self.data.cards.items()}, {a: 10 for a in ("a", "b", "s1", "s2", "c")})
        self.assertEqual(self.data.total_xp, 50)                      # 재통과(10-03)는 다시 세지 않는다
        self.assertEqual(self.data.xp_by_day("Asia/Seoul"), {date(2026, 10, d): 10 for d in (1, 2, 5, 6, 10)})
        self.assertEqual(self.data.xp_by_day("UTC")[date(2026, 10, 9)], 10)

    def test_study_dates_follow_timezone(self):
        kst = self.data.study_dates("Asia/Seoul")
        self.assertEqual(kst, {date(2026, 10, d) for d in (1, 2, 3, 5, 6, 10)})
        utc = self.data.study_dates("UTC")
        self.assertIn(date(2026, 10, 9), utc)
        self.assertNotIn(date(2026, 10, 10), utc)


if __name__ == "__main__":
    unittest.main()
