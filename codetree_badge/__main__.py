"""CLI: python -m codetree_badge --solutions <풀이 레포 경로> --out <출력 폴더>"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import curriculum, progress, render, render_level, render_xp, sample, solutions


def _parse_args(argv):
    ap = argparse.ArgumentParser(prog="python -m codetree_badge", description="코드트리 학습 현황 배지 생성기")
    ap.add_argument("--solutions", type=Path, help="코드트리 GitHub 연동 레포의 로컬 경로 (전체 커밋 이력 필요)")
    ap.add_argument("--out", type=Path, default=Path("dist"), help="출력 폴더 (기본: dist)")
    ap.add_argument("--cache", type=Path, help="커리큘럼 캐시 경로 (기본: <out>/curriculum-cache.json)")
    ap.add_argument("--offline", action="store_true", help="API 를 부르지 않고 캐시만 사용")
    ap.add_argument("--tz", default=os.environ.get("BADGE_TIMEZONE") or "Asia/Seoul", help="학습일 기준 타임존")
    ap.add_argument("--trail", default=os.environ.get("BADGE_TRAIL") or "auto",
                    help="auto(가장 많이 푼 트레일) 또는 1~6 고정")
    ap.add_argument("--daily-goal", default=os.environ.get("BADGE_DAILY_GOAL") or str(progress.DEFAULT_GOAL),
                    help="일일 목표 경험치 (코드트리 설정값: 25/50/90/140/240, 기본 50)")
    ap.add_argument("--today", type=date.fromisoformat, help="기준일 YYYY-MM-DD (기본: 오늘)")
    ap.add_argument("--source-repo", default=os.environ.get("CODETREE_REPO", ""), help="codetree.json 에 남길 풀이 레포 이름")
    ap.add_argument("--summary-file", type=Path, help="실행 요약(Markdown)을 덧붙일 파일 (예: $GITHUB_STEP_SUMMARY)")
    ap.add_argument("--sample", action="store_true", help="합성 데이터로 미리보기만 만든다")
    return ap.parse_args(argv)


def _summary_markdown(rep: progress.Report, source_repo: str, cur_source: str) -> str:
    d, s, r, x = rep.display, rep.streak, rep.recent, rep.xp
    lv = x.level
    recent = "-" if r is None else (
        f"{r.title} (Trail {r.trail_no} · {r.lesson}) · {r.day.isoformat()}" if r.trail_no else f"{r.title} · {r.day.isoformat()}")
    lines = [
        "### 코드트리 배지 갱신",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 풀이 레포 | {source_repo or '-'} |",
        f"| 표시 트레일 | Trail {d.no} · {d.level} ({d.passed}/{d.total}, {d.pct:.1f}%) |",
        f"| 전체 | {rep.passed}/{rep.total} ({rep.pct:.1f}%) |",
        f"| 스트릭 | 현재 {s.current}일 · 최장 {s.best}일 · 총 {s.total}일 |",
        f"| 최근 통과 | {recent} |",
        f"| 일일 경험치 | 오늘 {x.today}/{x.goal} XP · 최근 {len(x.days)}일 중 {x.goal_days}일 목표 달성 |",
        f"| 성장 레벨 | Lv.{lv.level} {lv.stage_name} ({lv.xp}/{lv.need} XP, 누적 {lv.total} XP) |",
        f"| 커리큘럼 | {cur_source} |",
    ]
    if rep.warnings:
        lines += ["", "**경고**", ""] + [f"- {w}" for w in rep.warnings]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = _parse_args(argv)
    try:
        ZoneInfo(args.tz)
    except (ZoneInfoNotFoundError, ValueError):
        print(f"오류: 알 수 없는 타임존 '{args.tz}' (예: Asia/Seoul)", file=sys.stderr)
        return 2
    today = args.today or datetime.now(ZoneInfo(args.tz)).date()
    try:
        daily_goal = int(str(args.daily_goal).strip())
        if daily_goal <= 0:
            raise ValueError
    except ValueError:
        print(f"오류: 일일 목표 경험치는 양의 정수여야 한다 (BADGE_DAILY_GOAL='{args.daily_goal}')", file=sys.stderr)
        return 2
    warnings: list[str] = []

    if args.sample:
        cur, sol = sample.build(args.today or sample.SAMPLE_TODAY, args.tz)
        today = args.today or sample.SAMPLE_TODAY
        cur_source = "sample"
    else:
        if not args.solutions or not (args.solutions / ".git").exists():
            print("오류: --solutions 에 풀이 레포의 git 체크아웃 경로를 지정한다", file=sys.stderr)
            return 2
        sol = solutions.scan(args.solutions)
        cache = args.cache or (args.out / "curriculum-cache.json")
        try:
            cur, cur_source, warnings = curriculum.load(cache, offline=args.offline)
        except curriculum.CurriculumError as e:
            print(f"오류: {e}", file=sys.stderr)
            return 1

    rep = progress.compute(cur, sol, today, args.tz, args.trail, daily_goal)
    rep.warnings[:0] = warnings

    args.out.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        (args.out / f"codetree-{theme}.svg").write_text(render.render(rep, theme), encoding="utf-8")
        (args.out / f"codetree-xp-{theme}.svg").write_text(render_xp.render_xp(rep, theme), encoding="utf-8")
        (args.out / f"codetree-level-{theme}.svg").write_text(render_level.render_level(rep, theme), encoding="utf-8")
    data = progress.to_json(rep, source_repo=args.source_repo, curriculum_source=cur_source)
    (args.out / "codetree.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    d, s = rep.display, rep.streak
    print(f"표시 트레일: Trail {d.no} ({d.passed}/{d.total}, {d.pct:.1f}%) | 전체 {rep.passed}/{rep.total} ({rep.pct:.1f}%)")
    print(f"레슨 상태: {d.pattern}")
    print(f"스트릭: 현재 {s.current}일, 최장 {s.best}일, 총 {s.total}일 | 커리큘럼: {cur_source}")
    x, lv = rep.xp, rep.xp.level
    print(f"경험치: 오늘 {x.today}/{x.goal} XP, 누적 {x.total} XP | 레벨: Lv.{lv.level} {lv.stage_name} ({lv.xp}/{lv.need})")
    for w in rep.warnings:
        print(f"::warning::{w}" if os.environ.get("GITHUB_ACTIONS") == "true" else f"경고: {w}")
    if args.summary_file:
        with open(args.summary_file, "a", encoding="utf-8") as f:
            f.write(_summary_markdown(rep, args.source_repo, cur_source))
    return 0


if __name__ == "__main__":
    sys.exit(main())
