"""코드트리 공개 커리큘럼 API 조회·정규화·캐시.

비로그인으로 열리는 `/api/v2/trails/progress/` 응답에서 구조(트레일 > 챕터 > 레슨 > 카드)만 쓴다.
진도 정보(progress_status)는 비로그인 응답에서 항상 "Ready" 라서 사용하지 않는다.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

API_URL = "https://api-prod.codetree.ai/api/v2/trails/progress/"
USER_AGENT = "CodeTree_badge_generator/1.0 (+https://github.com/kannikii/CodeTree_badge_generator)"
CACHE_SCHEMA = 1

# 트레일 alias → 영문 레벨 표기 (코드트리 화면의 "Trail 2. Novice Mid" 표기)
LEVEL_NAMES = {
    "codetree-101": "Introduction",
    "novice-low": "Novice Low",
    "novice-mid": "Novice Mid",
    "novice-high": "Novice High",
    "intermediate-low": "Intermediate Low",
    "intermediate-mid": "Intermediate Mid",
    "intermediate-high": "Intermediate High",
}


@dataclass(frozen=True)
class Card:
    alias: str
    type: str  # Introduction | Problem | Test


@dataclass
class Lesson:
    alias: str
    name: str
    chapter: str
    cards: list[Card] = field(default_factory=list)


@dataclass
class Trail:
    alias: str
    name: str
    order: int
    lessons: list[Lesson] = field(default_factory=list)

    @property
    def level(self) -> str:
        return LEVEL_NAMES.get(self.alias) or self.alias.replace("-", " ").title()

    @property
    def total(self) -> int:
        return sum(len(ls.cards) for ls in self.lessons)


@dataclass
class Curriculum:
    trails: list[Trail]

    def card_index(self) -> dict[str, tuple[Trail, int, Card]]:
        """카드 alias → (트레일, 레슨 인덱스, 카드)."""
        index: dict[str, tuple[Trail, int, Card]] = {}
        for trail in self.trails:
            for i, lesson in enumerate(trail.lessons):
                for card in lesson.cards:
                    index.setdefault(card.alias, (trail, i, card))
        return index


class CurriculumError(RuntimeError):
    pass


def _by_order(items):
    return sorted(items or [], key=lambda x: (x.get("order") is None, x.get("order") or 0))


def normalize(raw) -> Curriculum:
    """API 응답(JSON)을 Curriculum 으로 바꾼다. 레슨 없이 카드가 붙은 챕터는 레슨 1개로 본다."""
    if isinstance(raw, dict):
        raw = raw.get("results", raw.get("trails", []))
    if not isinstance(raw, list) or not raw:
        raise CurriculumError("커리큘럼 응답 형식이 예상과 다르다 (트레일 목록이 아님)")
    trails = []
    for c in _by_order(raw):
        trail = Trail(alias=str(c.get("alias", "")), name=str(c.get("name", "")), order=int(c.get("order") or 0))
        for ch in _by_order(c.get("chapters")):
            ch_name = str(ch.get("name", ""))
            lessons = ch.get("lessons")
            groups = _by_order(lessons) if lessons is not None else [ch]
            for ls in groups:
                cards = [Card(alias=str(cd.get("alias", "")), type=str(cd.get("type", "")))
                         for cd in _by_order(ls.get("curated_cards")) if cd.get("alias")]
                trail.lessons.append(Lesson(alias=str(ls.get("alias", "")), name=str(ls.get("name", "")),
                                            chapter=ch_name, cards=cards))
        trails.append(trail)
    return Curriculum(trails=trails)


def to_cache(cur: Curriculum) -> dict:
    """구조만 담은 결정적(deterministic) 캐시. 실행 시각을 넣지 않아 내용이 같으면 파일도 같다."""
    return {
        "schema": CACHE_SCHEMA,
        "source": API_URL,
        "trails": [
            {
                "alias": t.alias, "name": t.name, "order": t.order,
                "lessons": [
                    {"alias": ls.alias, "name": ls.name, "chapter": ls.chapter,
                     "cards": [[cd.alias, cd.type] for cd in ls.cards]}
                    for ls in t.lessons
                ],
            }
            for t in sorted(cur.trails, key=lambda tr: tr.order)
        ],
    }


def from_cache(data: dict) -> Curriculum:
    if not isinstance(data, dict) or data.get("schema") != CACHE_SCHEMA:
        raise CurriculumError("커리큘럼 캐시 형식이 다르다")
    trails = []
    for t in data.get("trails", []):
        trail = Trail(alias=t["alias"], name=t["name"], order=int(t["order"]))
        for ls in t.get("lessons", []):
            trail.lessons.append(Lesson(alias=ls["alias"], name=ls["name"], chapter=ls.get("chapter", ""),
                                        cards=[Card(alias=a, type=ty) for a, ty in ls.get("cards", [])]))
        trails.append(trail)
    return Curriculum(trails=trails)


def fetch(url: str = API_URL, timeout: float = 20.0, retries: int = 2):
    """공개 커리큘럼 API 를 호출한다. 실패하면 재시도 후 CurriculumError."""
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            last = e
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise CurriculumError(f"커리큘럼 API 호출 실패: {last}")


def load(cache_path: Path | None, offline: bool = False, fetcher=fetch) -> tuple[Curriculum, str, list[str]]:
    """(커리큘럼, 출처 'live'|'cache', 경고) 를 돌려준다. live 성공 시 캐시를 갱신한다."""
    warnings: list[str] = []
    if not offline:
        try:
            cur = normalize(fetcher())
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(to_cache(cur), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            return cur, "live", warnings
        except CurriculumError as e:
            warnings.append(f"{e} → 캐시를 사용한다")
    if cache_path is not None and cache_path.exists():
        try:
            return from_cache(json.loads(cache_path.read_text(encoding="utf-8"))), "cache", warnings
        except (CurriculumError, ValueError, KeyError) as e:
            raise CurriculumError(f"커리큘럼 캐시를 읽지 못했다: {e}") from e
    raise CurriculumError("커리큘럼을 가져올 수 없다 (API 실패, 캐시 없음)")
