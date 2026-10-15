"""풀이 레포(코드트리 GitHub 연동)의 git 이력에서 통과 카드와 학습일을 모은다.

코드트리 GitHub 연동은 카드를 통과할 때마다 아래 형태로 커밋한다.

    커밋 메시지  [Passed] <카드 제목> (<실행시간>, <메모리>)
    파일         trail<N>/<카드 제목>/README.md (+ 문제 카드는 코드 파일)
    README 1행   # [[개념]카드 제목](https://www.codetree.ai/trails/complete/curated-cards/<alias>)

경로 규칙에 기대지 않고 README 내용(카드 링크)으로 판별하며, 현재 트리가 아니라
커밋 이력의 각 시점 README 를 읽는다. 제목이 같은 서로 다른 카드가 한 폴더를 덮어써도
두 카드를 모두 잡기 위해서다.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from zoneinfo import ZoneInfo

CARD_LINK = re.compile(r"codetree\.ai/\S*?curated-cards/([A-Za-z0-9][A-Za-z0-9_\-]*)")
HEADER = re.compile(r"^\s*#\s*\[\[([^\]]*)\](.*)\]\((https?://[^)\s]+)\)\s*$")
CURRICULUM_ROW = re.compile(r"커리큘럼\s*\|\s*\[([^\]]+)\]")
PASSED_SUBJECT = re.compile(r"^\s*\[Passed\]\s*(.*?)(?:\s*\([^()]*\))?\s*$")
TRAIL_LABEL = re.compile(r"^\s*Trail\s+(\d+)")


@dataclass(frozen=True)
class CardRecord:
    """풀이 레포 README 한 장에서 읽은 카드 정보."""
    alias: str
    title: str
    tag: str = ""          # 개념 / 챌린지 / 테스트 ...
    path_label: str = ""   # "Trail 3 / 배열, 연결 리스트 / 단일 연결 리스트"

    @property
    def lesson_label(self) -> str:
        parts = [p.strip() for p in self.path_label.split("/") if p.strip()]
        return parts[-1] if len(parts) >= 2 else ""

    @property
    def trail_no(self) -> int | None:
        m = TRAIL_LABEL.match(self.path_label)
        return int(m.group(1)) if m else None


@dataclass(frozen=True)
class PassEvent:
    when: datetime         # timezone-aware
    sha: str
    title: str
    alias: str | None


@dataclass
class SolutionData:
    cards: dict[str, CardRecord] = field(default_factory=dict)       # alias → 최신 README 정보
    first_passed: dict[str, datetime] = field(default_factory=dict)  # alias → 최초 통과 시각
    events: list[PassEvent] = field(default_factory=list)            # 코드트리 커밋, 최신순

    @property
    def latest(self) -> PassEvent | None:
        return self.events[0] if self.events else None

    def study_dates(self, tz: str) -> set[date]:
        zone = ZoneInfo(tz)
        return {e.when.astimezone(zone).date() for e in self.events}


def parse_readme(text: str) -> CardRecord | None:
    """코드트리 카드 README 면 CardRecord, 아니면 None."""
    lines = text.splitlines()
    head = next((ln for ln in lines if ln.strip()), "")
    m_link = CARD_LINK.search(head)
    if not m_link:
        return None
    alias = m_link.group(1)
    tag, title = "", alias
    m = HEADER.match(head)
    if m:
        tag, title = m.group(1).strip(), m.group(2).strip() or alias
    m_cur = CURRICULUM_ROW.search(text)
    return CardRecord(alias=alias, title=title, tag=tag, path_label=m_cur.group(1).strip() if m_cur else "")


def title_from_subject(subject: str) -> str:
    m = PASSED_SUBJECT.match(subject)
    return m.group(1).strip() if m else subject.strip()


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    res = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=false", *args],
                         input=stdin, capture_output=True, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])} 실패: {res.stderr.decode('utf-8', 'replace').strip()}")
    return res.stdout


def _read_log(repo: Path):
    """(sha, 작성 시각, 메시지, [(상태, 경로)]) 를 최신순으로."""
    raw = _git(repo, "log", "--no-merges", "--name-status", "-z",
               "--format=%x1e%H%x1f%aI%x1f%s").decode("utf-8", "replace")
    commits = []
    for rec in raw.split("\x1e"):
        if not rec.strip():
            continue
        header, _, rest = rec.partition("\x00")
        sha, when, subject = (header.split("\x1f") + ["", "", ""])[:3]
        tokens = [t.lstrip("\n") for t in rest.split("\x00")]
        changes, i = [], 0
        while i < len(tokens):
            status = tokens[i]
            if not status:
                i += 1
                continue
            if status[0] in "RC" and i + 2 < len(tokens):      # 이름 변경: 이전 경로, 새 경로
                changes.append((status[0], tokens[i + 2]))
                i += 3
            elif i + 1 < len(tokens):
                changes.append((status[0], tokens[i + 1]))
                i += 2
            else:
                break
        commits.append((sha, datetime.fromisoformat(when), subject, changes))
    return commits


def _read_blobs(repo: Path, specs: list[str]) -> dict[str, str | None]:
    """`<sha>:<path>` 목록을 git cat-file --batch 로 한 번에 읽는다."""
    if not specs:
        return {}
    out = _git(repo, "cat-file", "--batch", stdin=("\n".join(specs) + "\n").encode("utf-8"))
    result: dict[str, str | None] = {}
    pos = 0
    for spec in specs:
        nl = out.index(b"\n", pos)
        header = out[pos:nl].decode("utf-8", "replace")
        pos = nl + 1
        if header.endswith(" missing") or header.endswith(" ambiguous"):
            result[spec] = None
            continue
        size = int(header.rsplit(" ", 1)[1])
        result[spec] = out[pos:pos + size].decode("utf-8", "replace")
        pos += size + 1  # 내용 뒤 개행
    return result


def scan(repo: Path) -> SolutionData:
    commits = _read_log(repo)

    # 커밋마다 '건드린 파일이 있는 폴더의 README.md' 를 그 시점 기준으로 읽는다(루트 폴더 제외).
    wanted: dict[str, list[str]] = {}
    specs: list[str] = []
    for sha, _, _, changes in commits:
        dirs = []
        for status, path in changes:
            if status == "D":
                continue
            parent = PurePosixPath(path).parent
            if str(parent) in ("", "."):
                continue
            readme = f"{parent}/README.md"
            if readme not in dirs:
                dirs.append(readme)
        wanted[sha] = dirs
        specs.extend(f"{sha}:{p}" for p in dirs)
    blobs = _read_blobs(repo, specs)

    data = SolutionData()
    for sha, when, subject, changes in commits:  # 최신순
        added = {path for status, path in changes if status in "AR" and path.endswith("README.md")}
        recs = []
        for readme in wanted[sha]:
            text = blobs.get(f"{sha}:{readme}")
            rec = parse_readme(text) if text else None
            if rec:
                recs.append((readme, rec))
        is_passed = subject.lstrip().startswith("[Passed]")
        # 메시지 형식이 바뀌어도 '카드 README 가 새로 추가된 커밋' 이면 통과로 본다.
        if not is_passed and not any(readme in added for readme, _ in recs):
            continue
        for _, rec in recs:
            data.cards.setdefault(rec.alias, rec)
            prev = data.first_passed.get(rec.alias)
            data.first_passed[rec.alias] = when if prev is None or when < prev else prev
        primary = recs[0][1] if recs else None
        data.events.append(PassEvent(when=when, sha=sha,
                                     title=primary.title if primary else title_from_subject(subject),
                                     alias=primary.alias if primary else None))
    data.events.sort(key=lambda e: e.when, reverse=True)
    return data
