"""테스트용 헬퍼: 임시 git 레포와 작은 커리큘럼을 만든다."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from codetree_badge.curriculum import Card, Curriculum, Lesson, Trail


def readme(alias: str, title: str, tag: str = "챌린지", path: str = "Trail 2 / 시뮬레이션 II / dx dy technique",
           xp: int = 10) -> str:
    trail_alias = {"0": "codetree-101", "1": "novice-low", "2": "novice-mid", "3": "novice-high"}.get(path.split()[1], "x")
    return (f"# [[{tag}]{title}](https://www.codetree.ai/trails/complete/curated-cards/{alias})\n\n"
            "| 항목 | 내용 |\n|---|---|\n| 분류 | Trail |\n"
            f"| 커리큘럼 | [{path}](https://www.codetree.ai/trail-info/{trail_alias}/) |\n"
            f"| 난이도 | 쉬움 |\n| 경험치 | {xp} XP |\n")


def make_repo(root: Path, commits: list[dict]) -> Path:
    """commits: [{"message", "when"(ISO), "files": {경로: 내용 | None(삭제)}}] 순서대로 커밋한다."""
    root.mkdir(parents=True, exist_ok=True)
    base_env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

    def git(*args, env=None):
        subprocess.run(["git", "-C", str(root), "-c", "user.name=tester", "-c", "user.email=t@example.com",
                        "-c", "commit.gpgsign=false", *args],
                       check=True, capture_output=True, env=env or base_env)

    git("init", "-q", "-b", "main")
    for c in commits:
        for path, content in c["files"].items():
            p = root / path
            if content is None:
                p.unlink()
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
        git("add", "-A")
        env = {**base_env, "GIT_AUTHOR_DATE": c["when"], "GIT_COMMITTER_DATE": c["when"]}
        git("commit", "-q", "--allow-empty", "-m", c["message"], env=env)
    return root


def lesson(alias: str, cards: list[tuple[str, str]], name: str | None = None, chapter: str = "챕터") -> Lesson:
    return Lesson(alias=alias, name=name or alias, chapter=chapter, cards=[Card(a, t) for a, t in cards])


def small_curriculum() -> Curriculum:
    """Trail 0(제외 대상) + Trail 1~3 의 작은 커리큘럼."""
    ipt = lambda p: [(f"{p}-i", "Introduction"), (f"{p}-p1", "Problem"), (f"{p}-p2", "Problem"), (f"{p}-t", "Test")]
    return Curriculum(trails=[
        Trail("codetree-101", "코드트리 입문", 0, [lesson("z1", ipt("z1"))]),
        Trail("novice-low", "프로그래밍 기초", 1, [lesson("a1", ipt("a1")), lesson("a2", ipt("a2"))]),
        Trail("novice-mid", "프로그래밍 연습", 2, [lesson("b1", ipt("b1")), lesson("b2", ipt("b2")),
                                                   lesson("b3", ipt("b3"))]),
        Trail("novice-high", "자료구조 알고리즘", 3, [lesson("c1", ipt("c1"))]),
    ])
