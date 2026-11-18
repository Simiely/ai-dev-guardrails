from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .canary import render_canary, run_canary
from .card import build_card
from .config import load_config
from .contract import diff_snapshot, write_snapshot
from .custody import approve_tests, check_tests, lock_tests
from .doctor import run_doctor
from .eval_routing import evaluate_routing
from .graph import affected_tests
from .hook import evaluate_pre_tool, session_start_text
from .init import init_project, next_steps
from .lint import lint_manual
from .manual import load_chapters, load_manual
from .metrics import ingest_junit, metrics_report, record_run, render_metrics
from .mutation import run_mutation
from .quality import quality_report
from .report import build_report, render_report
from .risk import classify
from .route import Task, brief_text, load_task, select_chapters
from .state import active_task, handoff_text, init_state, load_state, set_active, update_state
from .sync import sync_views
from .task import create_task
from .trace import add_raw_source, raw_sources, verify_trace
from .util import GuardrailsError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guardrails",
        description="Architecture contract layer + manual router for coding agents.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--root", default=".", help="project root (default: .)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="copy the pack into a project")
    p_init.add_argument("--target", default=".")
    p_init.add_argument("--source", default=None)
    p_init.add_argument("--mode", choices=["greenfield", "brownfield"], default="greenfield")
    p_init.add_argument("--dry-run", action="store_true")
    p_init.add_argument("--force", action="store_true")

    p_lint = sub.add_parser("lint-manual", help="lint the always-on card and chapters")
    p_lint.add_argument("--json", action="store_true")

    p_brief = sub.add_parser("brief", help="select 1-3 chapters for a task")
    p_brief.add_argument("--task", default=None)
    p_brief.add_argument("--files", nargs="*", default=[])
    p_brief.add_argument("--type", default="")
    p_brief.add_argument("--unfamiliar", action="store_true")
    p_brief.add_argument("--json", action="store_true")

    p_task = sub.add_parser("task", help="create a task scaffold")
    tsub = p_task.add_subparsers(dest="task_command", required=True)
    p_task_new = tsub.add_parser("new")
    p_task_new.add_argument("--id", required=True)
    p_task_new.add_argument("--title", required=True)
    p_task_new.add_argument("--type", default="feature")
    p_task_new.add_argument("--risk", default="R1", choices=["R0", "R1", "R2", "R3"])
    p_task_new.add_argument("--files", nargs="*", default=[])

    p_trace = sub.add_parser("verify-trace", help="verify claim sources and hashes")
    p_trace.add_argument("--task", default=None)
    p_trace.add_argument("--all", action="store_true")
    p_trace.add_argument("--require", action="store_true", help="fail on claims without a source")
    p_trace.add_argument("--json", action="store_true")

    p_raw = sub.add_parser("raw", help="manage immutable raw sources")
    rsub = p_raw.add_subparsers(dest="raw_command", required=True)
    p_raw_add = rsub.add_parser("add")
    p_raw_add.add_argument("--task", required=True)
    p_raw_add.add_argument("--from", dest="source", required=True)
    p_raw_add.add_argument("--origin", default="")
    p_raw_add.add_argument("--force", action="store_true")
    p_raw_list = rsub.add_parser("list")
    p_raw_list.add_argument("--task", required=True)
    p_raw_list.add_argument("--json", action="store_true")

    p_eval = sub.add_parser("eval-routing", help="measure routing recall/zero-load/over-load")
    p_eval.add_argument("--suite", default=None)
    p_eval.add_argument("--json", action="store_true")

    p_sync = sub.add_parser("sync", help="generate AGENTS/Claude/Kiro/Cursor views")
    p_sync.add_argument("--check", action="store_true")
    p_sync.add_argument("--force", action="store_true", help="overwrite files without the generated marker")
    p_sync.add_argument("--json", action="store_true")

    p_contract = sub.add_parser("contract", help="snapshot and diff contracts")
    csub = p_contract.add_subparsers(dest="contract_command", required=True)
    p_snap = csub.add_parser("snapshot")
    p_snap.add_argument("--path", required=True)
    p_snap.add_argument("--out", required=True)
    p_diff = csub.add_parser("diff")
    p_diff.add_argument("--base", required=True)
    p_diff.add_argument("--current", required=True)
    p_diff.add_argument("--json", action="store_true")

    p_affected = sub.add_parser("affected", help="list tests affected by changed files")
    p_affected.add_argument("--files", nargs="*", default=[])
    p_affected.add_argument("--diff", action="store_true")
    p_affected.add_argument("--base", default="main")
    p_affected.add_argument("--json", action="store_true")

    p_mutation = sub.add_parser("mutation", help="run the project mutation command on changed files")
    p_mutation.add_argument("--files", nargs="*", default=[])
    p_mutation.add_argument("--diff", action="store_true")
    p_mutation.add_argument("--base", default="main")
    p_mutation.add_argument("--require", action="store_true", help="fail if mutation is not configured")
    p_mutation.add_argument("--json", action="store_true")

    p_state = sub.add_parser("state", help="manage task state and handoff")
    ssub = p_state.add_subparsers(dest="state_command", required=True)
    p_state_init = ssub.add_parser("init")
    p_state_init.add_argument("--task", required=True)
    p_state_init.add_argument("--task-file", default=None)
    p_state_show = ssub.add_parser("show")
    p_state_show.add_argument("--task", required=True)
    p_state_show.add_argument("--json", action="store_true")
    p_state_next = ssub.add_parser("next")
    p_state_next.add_argument("--task", required=True)
    p_state_next.add_argument("--next", required=True)
    p_state_next.add_argument("--chapter", default=None)
    p_state_active = ssub.add_parser("set-active")
    p_state_active.add_argument("--task", required=True)
    p_state_handoff = ssub.add_parser("handoff")
    p_state_handoff.add_argument("--task", default=None)

    p_canary = sub.add_parser("canary", help="run canary suite and compare with baseline")
    p_canary.add_argument("--suite", default=None)
    p_canary.add_argument("--update-baseline", action="store_true")
    p_canary.add_argument("--json", action="store_true")

    p_report = sub.add_parser("report", help="show current structural quality signals")
    p_report.add_argument("--json", action="store_true")

    p_metrics = sub.add_parser("metrics", help="record and report local run metrics")
    msub = p_metrics.add_subparsers(dest="metrics_command", required=True)
    p_metrics_record = msub.add_parser("record")
    p_metrics_record.add_argument("--task", required=True)
    p_metrics_record.add_argument("--status", choices=["pass", "fail"], required=True)
    p_metrics_record.add_argument("--tests-total", type=int, default=0)
    p_metrics_record.add_argument("--tests-failed", type=int, default=0)
    p_metrics_record.add_argument("--duration", type=float, default=0.0)
    p_metrics_record.add_argument("--rework", action="store_true")
    p_metrics_record.add_argument("--note", default="")
    p_metrics_record.add_argument("--json", action="store_true")
    p_metrics_junit = msub.add_parser("ingest-junit")
    p_metrics_junit.add_argument("--file", required=True)
    p_metrics_junit.add_argument("--task", required=True)
    p_metrics_junit.add_argument("--json", action="store_true")
    p_metrics_report = msub.add_parser("report")
    p_metrics_report.add_argument("--json", action="store_true")

    p_card = sub.add_parser("card", help="generate a consequence card for a task")
    p_card.add_argument("--task", required=True)
    p_card.add_argument("--files", nargs="*", default=[])
    p_card.add_argument("--out", default=None)
    p_card.add_argument("--json", action="store_true")

    p_quality = sub.add_parser("quality", help="check complexity, function length, duplicate blocks")
    p_quality.add_argument("--files", nargs="*", default=[])
    p_quality.add_argument("--diff", action="store_true")
    p_quality.add_argument("--base", default="main")
    p_quality.add_argument("--max-complexity", type=int, default=10)
    p_quality.add_argument("--max-function-length", type=int, default=50)
    p_quality.add_argument("--min-duplicate-lines", type=int, default=5)
    p_quality.add_argument("--fail-on", action="store_true")
    p_quality.add_argument("--json", action="store_true")

    p_risk = sub.add_parser("risk", help="classify changed files as R0-R3")
    p_risk.add_argument("--files", nargs="*", default=[])
    p_risk.add_argument("--diff", action="store_true")
    p_risk.add_argument("--base", default="main")
    p_risk.add_argument("--json", action="store_true")

    p_lock = sub.add_parser("test-lock", help="lock test files after red")
    p_lock.add_argument("--task", required=True)
    p_lock.add_argument("--files", nargs="*", default=[])
    p_lock.add_argument("--json", action="store_true")

    p_check = sub.add_parser("test-check", help="check locked test files for changes")
    p_check.add_argument("--task", required=True)
    p_check.add_argument("--json", action="store_true")

    p_approve = sub.add_parser("test-approve", help="approve a test change")
    p_approve.add_argument("--task", required=True)
    p_approve.add_argument("--reason", required=True)
    p_approve.add_argument("--json", action="store_true")

    p_doctor = sub.add_parser("doctor", help="check config, manual, views, commands, CI, hooks")
    p_doctor.add_argument("--json", action="store_true")

    p_run = sub.add_parser("run", help="run a command from guardrails.yaml")
    p_run.add_argument("name")

    p_hook = sub.add_parser("hook", help="Claude Code hook adapter")
    p_hook.add_argument("--event", choices=["pre-tool", "session-start", "stop"], required=True)
    p_hook.add_argument("--payload", default=None, help="JSON payload (for tests)")
    return parser


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _input_path(root: Path, value: str) -> Path:
    """Resolve an input path from cwd first, then from --root."""
    path = Path(value)
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    return (root / path).resolve()


def _git_changed_files(root: Path, base: str) -> list[str]:
    git = shutil.which("git")
    if not git:
        candidate = Path(r"C:\Program Files\Git\cmd\git.exe")
        git = str(candidate) if candidate.exists() else None
    if not git:
        raise GuardrailsError("git not found; pass --files explicitly")
    proc = subprocess.run(
        [git, "diff", "--name-only", f"{base}...HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GuardrailsError(proc.stderr.strip() or "git diff failed")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def cmd_lint(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    card, chapters = load_manual(root, config)
    result = lint_manual(root, config, card, chapters)
    if args.json:
        _print_json(result)
    else:
        for item in result["errors"]:
            print(f"ERROR {item['code']} {item['path']}: {item['message']}")
        for item in result["warnings"]:
            print(f"WARN  {item['code']} {item['path']}: {item['message']}")
        status = "PASS" if not result["errors"] else "FAIL"
        print(
            f"LINT MANUAL: {status} "
            f"(errors={len(result['errors'])}, warnings={len(result['warnings'])}, "
            f"chapters={result['chapters']}, card_lines={result['card_lines']})"
        )
    return 0 if not result["errors"] else 1


def cmd_brief(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    chapters = load_chapters(root, config)
    if args.task:
        task = load_task(_input_path(root, args.task))
    else:
        task = Task(id="adhoc", type=args.type, files=list(args.files), unfamiliar=args.unfamiliar)
    if args.files:
        task.files = list(args.files)
    if args.type:
        task.type = args.type
    if args.unfamiliar:
        task.unfamiliar = True
    result = select_chapters(task, config, chapters)
    if args.task:
        sources = raw_sources(root, task.id)
        if sources:
            result["raw_sources"] = sources
    if args.json:
        _print_json(result)
    else:
        print(brief_text(result, chapters))
    return 0


def cmd_eval(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    chapters = load_chapters(root, config)
    suite = _input_path(root, args.suite) if args.suite else root / "eval" / "routing"
    if not suite.exists():
        raise GuardrailsError(f"missing routing suite: {suite}")
    result = evaluate_routing(root, config, chapters, suite)
    if args.json:
        _print_json(result)
    else:
        for case in result["cases"]:
            status = "PASS" if case["passed"] else "FAIL"
            print(
                f"{status} {case['id']}: selected={case['selected']} "
                f"missing={case['missing']} extra={case['extra']}"
            )
        status = "PASS" if result["passed"] and result["zero_load"] == 0 and result["recall"] >= 0.9 else "FAIL"
        print(
            f"EVAL ROUTING: {status} "
            f"(cases={result['total']}, recall={result['recall']}, "
            f"zero_load={result['zero_load']}, over_load={result['over_load']}, "
            f"token_avg={result['token_avg']})"
        )
    return 0 if result["passed"] and result["zero_load"] == 0 and result["recall"] >= 0.9 else 1


def cmd_sync(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    result = sync_views(root, config, check=args.check, force=args.force)
    if args.json:
        _print_json(result)
    else:
        for item in result["conflicts"]:
            print(f"CONFLICT {item['path']} (unmanaged file; merge manually or use --force)")
        if result["drift"]:
            for item in result["drift"]:
                print(f"{item['status'].upper()} {item['path']}")
        if result["written"]:
            for path in result["written"]:
                print(f"WROTE {path}")
        failed = bool(result["conflicts"]) or (args.check and bool(result["drift"]))
        status = "PASS" if not failed else "FAIL"
        print(
            f"SYNC: {status} "
            f"(written={len(result['written'])}, drift={len(result['drift'])}, "
            f"conflicts={len(result['conflicts'])})"
        )
    if args.check:
        return 1 if result["drift"] or result["conflicts"] else 0
    return 1 if result["conflicts"] else 0


def cmd_contract(root: Path, args: argparse.Namespace) -> int:
    if args.contract_command == "snapshot":
        result = write_snapshot(_input_path(root, args.path), _path(root, args.out))
        print(f"SNAPSHOT {result['path']} {result['hash']}")
        return 0
    if args.contract_command == "diff":
        result = diff_snapshot(_input_path(root, args.base), _input_path(root, args.current))
        if args.json:
            _print_json(result)
        else:
            for item in result["breaking"]:
                print(f"BREAKING {item['path']} {item['kind']} {item['detail']}")
            for item in result["non_breaking"]:
                print(f"OK       {item['path']} {item['kind']} {item['detail']}")
            print(
                f"CONTRACT: {'BREAKING' if result['summary']['breaking'] else 'PASS'} "
                f"(breaking={result['summary']['breaking']}, "
                f"non_breaking={result['summary']['non_breaking']})"
            )
        return 1 if result["summary"]["breaking"] else 0
    raise GuardrailsError("unknown contract subcommand")


def cmd_affected(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    files = list(args.files)
    if args.diff:
        files.extend(_git_changed_files(root, args.base))
    if not files:
        raise GuardrailsError("pass --files or --diff")
    result = affected_tests(root, config, files)
    if args.json:
        _print_json(result)
    else:
        print(f"AFFECTED: {len(result['affected_tests'])} tests (fallback={result['fallback']})")
        for test in result["affected_tests"]:
            reasons = result["reasons"].get(test, [])
            print(f"- {test}" + (f"  ({reasons[0]})" if reasons else ""))
        print(
            f"graph: files={result['stats']['files']}, "
            f"tests={result['stats']['tests']}, edges={result['stats']['edges']}"
        )
    return 0


def cmd_mutation(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    files = list(args.files)
    if args.diff:
        files.extend(_git_changed_files(root, args.base))
    if not files:
        raise GuardrailsError("pass --files or --diff")
    result = run_mutation(root, config, files)
    if args.json:
        _print_json(result)
    else:
        if not result["ran"]:
            print(f"MUTATION: SKIP ({result['reason']})")
            print(f"hint: {result['hint']}")
        else:
            print(f"MUTATION: {'PASS' if result['exit_code'] == 0 else 'FAIL'} (exit={result['exit_code']})")
            print(f"files: {', '.join(result['files'])}")
    if not result["ran"]:
        return 2 if args.require else 0
    return int(result["exit_code"] or 0)


def cmd_state(root: Path, args: argparse.Namespace) -> int:
    if args.state_command == "init":
        task_file = _input_path(root, args.task_file) if args.task_file else None
        data = init_state(root, args.task, task_file)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if args.state_command == "show":
        data = load_state(root, args.task)
        if data is None:
            raise GuardrailsError(f"no state for task {args.task!r}")
        if args.json:
            _print_json(data)
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if args.state_command == "next":
        current = load_state(root, args.task)
        step = int(current.get("step", 0)) + 1 if current else 1
        fields = {"next": args.next, "step": step}
        if args.chapter:
            fields["chapter"] = args.chapter
        data = update_state(root, args.task, **fields)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if args.state_command == "set-active":
        set_active(root, args.task)
        print(f"ACTIVE: {args.task}")
        return 0
    if args.state_command == "handoff":
        print(handoff_text(root, args.task))
        return 0
    raise GuardrailsError("unknown state subcommand")


def cmd_metrics(root: Path, args: argparse.Namespace) -> int:
    if args.metrics_command == "record":
        result = record_run(
            root,
            task=args.task,
            status=args.status,
            tests_total=args.tests_total,
            tests_failed=args.tests_failed,
            duration=args.duration,
            rework=args.rework,
            note=args.note,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"METRICS: recorded {args.task} {args.status}")
        return 0
    if args.metrics_command == "ingest-junit":
        result = ingest_junit(root, _input_path(root, args.file), args.task)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"METRICS: ingested {args.file} -> {result['status']}")
        return 0
    if args.metrics_command == "report":
        result = metrics_report(root)
        if args.json:
            _print_json(result)
        else:
            print(render_metrics(result))
        return 0
    raise GuardrailsError("unknown metrics subcommand")


def cmd_canary(root: Path, args: argparse.Namespace) -> int:
    suite = _input_path(root, args.suite) if args.suite else root / "eval" / "canary.yaml"
    result = run_canary(root, suite, update_baseline=args.update_baseline)
    if args.json:
        _print_json(result)
    else:
        print(render_canary(result))
    return 0 if result["ok"] else 1


def cmd_report(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    result = build_report(root, config)
    if args.json:
        _print_json(result)
    else:
        print(render_report(result))
    return 0


def cmd_card(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    result = build_card(root, config, _input_path(root, args.task), args.files or None)
    if args.out:
        out = _path(root, args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result["markdown"].rstrip() + "\n", encoding="utf-8")
        print(f"CARD: {out}")
    elif args.json:
        _print_json(result)
    else:
        print(result["markdown"])
    return 0


def cmd_quality(root: Path, args: argparse.Namespace) -> int:
    files = list(args.files)
    if args.diff:
        files.extend(_git_changed_files(root, args.base))
    if not files:
        raise GuardrailsError("pass --files or --diff")
    result = quality_report(
        root,
        files,
        max_complexity=args.max_complexity,
        max_function_length=args.max_function_length,
        min_duplicate_lines=args.min_duplicate_lines,
    )
    if args.json:
        _print_json(result)
    else:
        print(
            f"QUALITY: functions={result['summary']['functions']}, "
            f"violations={result['summary']['violations']}, "
            f"duplicates={result['summary']['duplicate_blocks']}"
        )
        for item in result["violations"]:
            print(f"- {item['kind']}: {item['file']} {item.get('function', '')} ({item['detail']})")
        for item in result["duplicates"]:
            locations = ", ".join(f"{loc['file']}:{loc['line']}" for loc in item["locations"])
            print(f"- duplicate {item['lines']} lines: {locations}")
        for item in result["unsupported"]:
            print(f"- unsupported: {item}")
    if args.fail_on and (result["violations"] or result["duplicates"]):
        return 1
    return 0


def cmd_risk(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    files = list(args.files)
    if args.diff:
        files.extend(_git_changed_files(root, args.base))
    if not files:
        raise GuardrailsError("pass --files or --diff")
    result = classify(files, config)
    if args.json:
        _print_json(result)
    else:
        print(f"RISK: {result['level']}")
        for reason in result["reasons"]:
            print(f"- {reason}")
    return 0


def cmd_test_lock(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    result = lock_tests(root, config, args.task, args.files or None)
    if args.json:
        _print_json(result)
    else:
        print(f"TEST LOCK: {result['locked']} files for task {result['task']}")
    return 0


def cmd_test_check(root: Path, args: argparse.Namespace) -> int:
    result = check_tests(root, args.task)
    if args.json:
        _print_json(result)
    else:
        if not result["locked"]:
            print(f"TEST CHECK: no lock for task {result['task']} (PASS)")
        elif result["ok"]:
            print(f"TEST CHECK: PASS (task {result['task']})")
        else:
            print(f"TEST CHECK: FAIL (task {result['task']})")
            for item in result["changed"]:
                print(f"- changed: {item}")
            for item in result["missing"]:
                print(f"- missing: {item}")
            if result["approved"]:
                print("- approved edit detected; run test-lock again to re-baseline")
    return 0 if result["ok"] else 1


def cmd_test_approve(root: Path, args: argparse.Namespace) -> int:
    result = approve_tests(root, args.task, args.reason)
    if args.json:
        _print_json(result)
    else:
        print(f"TEST APPROVE: task {result['task']} — {result['reason']}")
    return 0


def cmd_doctor(root: Path, args: argparse.Namespace) -> int:
    result = run_doctor(root)
    if args.json:
        _print_json(result)
    else:
        for check in result["checks"]:
            print(f"{check['status']:4} {check['name']}: {check['detail']}")
        print(f"DOCTOR: {'PASS' if result['passed'] else 'FAIL'}")
    return 0 if result["passed"] else 1


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.target).resolve()
    source = Path(args.source).resolve() if args.source else None
    result = init_project(
        target,
        source=source,
        force=args.force,
        mode=args.mode,
        dry_run=args.dry_run,
    )
    print(next_steps(result))
    return 0


def cmd_task(root: Path, args: argparse.Namespace) -> int:
    if args.task_command == "new":
        result = create_task(
            root,
            task_id=args.id,
            title=args.title,
            task_type=args.type,
            risk=args.risk,
            files=args.files or None,
        )
        print(f"TASK: {result['task']} -> {result['path']}")
        for name in result["created"]:
            print(f"- {name}")
        print(f"next: guardrails brief --task specs/{result['task']}/task.yaml")
        return 0
    raise GuardrailsError("unknown task subcommand")


def cmd_verify_trace(root: Path, args: argparse.Namespace) -> int:
    if args.all and args.task:
        raise GuardrailsError("use either --task or --all, not both")
    result = verify_trace(
        root,
        task=args.task,
        all_tasks=args.all,
        require_sources=args.require,
    )
    if args.json:
        _print_json(result)
    else:
        for warning in result["warnings"]:
            print(f"WARN  {warning}")
        for error in result["errors"]:
            print(f"ERROR {error}")
        print(
            f"TRACE: {'PASS' if result['ok'] else 'FAIL'} "
            f"(tasks={result['checked']}, errors={len(result['errors'])}, "
            f"warnings={len(result['warnings'])})"
        )
    return 0 if result["ok"] else 1


def cmd_raw(root: Path, args: argparse.Namespace) -> int:
    if args.raw_command == "add":
        entry = add_raw_source(
            root,
            args.task,
            _input_path(root, args.source),
            origin=args.origin,
            force=args.force,
        )
        print(f"RAW: {entry['path']} {entry['sha256']}")
        return 0
    if args.raw_command == "list":
        sources = raw_sources(root, args.task)
        if args.json:
            _print_json(sources)
        else:
            for item in sources:
                print(f"{item.get('path')}  {item.get('origin', '')}  {item.get('sha256', '')}")
        return 0
    raise GuardrailsError("unknown raw subcommand")


def cmd_hook(root: Path, args: argparse.Namespace) -> int:
    if args.event == "session-start":
        print(session_start_text(root))
        return 0
    if args.event == "stop":
        return 0
    raw = args.payload
    if raw is None:
        raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GuardrailsError(f"invalid hook payload: {exc}") from exc
    try:
        config = load_config(root)
    except GuardrailsError:
        return 0
    result = evaluate_pre_tool(root, config, payload)
    if result["decision"] == "deny":
        print(result["reason"], file=sys.stderr)
        return 2
    return 0


def cmd_run(root: Path, args: argparse.Namespace) -> int:
    config = load_config(root)
    command = config.get("commands", {}).get(args.name)
    if not command:
        raise GuardrailsError(f"unknown command {args.name!r} in guardrails.yaml")
    if "TODO" in command or re.search(r"<[^>]+>", command):
        raise GuardrailsError(f"command {args.name!r} is not configured: {command}")
    proc = subprocess.run(command, shell=True, cwd=root)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.command == "init":
            return cmd_init(args)
        if args.command == "lint-manual":
            return cmd_lint(root, args)
        if args.command == "brief":
            return cmd_brief(root, args)
        if args.command == "task":
            return cmd_task(root, args)
        if args.command == "verify-trace":
            return cmd_verify_trace(root, args)
        if args.command == "raw":
            return cmd_raw(root, args)
        if args.command == "eval-routing":
            return cmd_eval(root, args)
        if args.command == "sync":
            return cmd_sync(root, args)
        if args.command == "contract":
            return cmd_contract(root, args)
        if args.command == "affected":
            return cmd_affected(root, args)
        if args.command == "mutation":
            return cmd_mutation(root, args)
        if args.command == "state":
            return cmd_state(root, args)
        if args.command == "canary":
            return cmd_canary(root, args)
        if args.command == "report":
            return cmd_report(root, args)
        if args.command == "metrics":
            return cmd_metrics(root, args)
        if args.command == "card":
            return cmd_card(root, args)
        if args.command == "quality":
            return cmd_quality(root, args)
        if args.command == "risk":
            return cmd_risk(root, args)
        if args.command == "test-lock":
            return cmd_test_lock(root, args)
        if args.command == "test-check":
            return cmd_test_check(root, args)
        if args.command == "test-approve":
            return cmd_test_approve(root, args)
        if args.command == "doctor":
            return cmd_doctor(root, args)
        if args.command == "run":
            return cmd_run(root, args)
        if args.command == "hook":
            return cmd_hook(root, args)
        raise GuardrailsError(f"unknown command: {args.command}")
    except GuardrailsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
