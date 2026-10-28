#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from installer.safety import CapsuleSafetyError, confined_local_path, validate_core_commit
from installer.durable_state import (DurableStateError, EVENTS, verify_durable_state, sealed_changes, event_changes, INDEX)
from installer.github_publish import publish_files
from installer.service_agent import (
    ServiceAgentModelError,
    build_service_recovery_pack,
    service_clean_install_changes,
    service_readiness_snapshot,
    service_repair_changes,
    validate_service_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "service-agent-templates"

def target_root(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise SystemExit(f"target does not exist or is not a directory: {path}")
    return path

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def load_snapshot(target: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for rel in ("AI_CONTEXT.md", "AGENTS.md"):
        p = target / rel
        if p.exists() and p.is_file():
            files[rel] = read_text(p)
    context = target / ".context"
    if context.exists():
        if context.is_symlink() or not context.is_dir():
            raise SystemExit("unsafe .context path")
        for p in sorted(context.rglob("*")):
            if p.is_file():
                rel = p.relative_to(target).as_posix()
                confined_local_path(target, rel)
                files[rel] = read_text(p)
    return files

def apply_changes(target: Path, changes: dict[str, str | None]) -> None:
    for rel, content in changes.items():
        p = confined_local_path(target, rel)
        if content is None:
            if p.exists():
                p.unlink()
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".service-agent.tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, p)

def actual_branch(target: Path) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(target), "branch", "--show-current"],
            text=True, capture_output=True, check=True
        ).stdout.strip() or None
    except Exception:
        return None

def ensure_branch(target: Path, requested: str) -> None:
    actual = actual_branch(target)
    if actual and actual != requested:
        raise SystemExit(f"target checkout branch mismatch: requested {requested!r}, actual {actual!r}")

def source_commit(explicit: str | None) -> str:
    if explicit:
        return validate_core_commit(explicit)
    try:
        sha = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True, capture_output=True, check=True
        ).stdout.strip()
        return validate_core_commit(sha)
    except Exception as exc:
        raise SystemExit("--source-commit is required outside a Git checkout") from exc

def cmd_install(args) -> int:
    target = target_root(args.target)
    ensure_branch(target, args.branch)
    try:
        changes = service_clean_install_changes(
            load_snapshot(target), TEMPLATES,
            repository=args.repository, branch=args.branch,
            core_commit=source_commit(args.source_commit),
            agent_id=args.agent_id, role=args.role, specialization=args.specialization,
        )
        apply_changes(target, changes)
    except (ServiceAgentModelError, CapsuleSafetyError) as exc:
        print(f"Service Agent install: FAIL\n  - {exc}")
        return 2
    return cmd_validate(argparse.Namespace(target=str(target)))

def cmd_repair(args) -> int:
    target = target_root(args.target)
    ensure_branch(target, args.branch)
    try:
        changes = service_repair_changes(
            load_snapshot(target), TEMPLATES,
            repository=args.repository, branch=args.branch,
            core_commit=source_commit(args.source_commit),
        )
        apply_changes(target, changes)
    except (ServiceAgentModelError, CapsuleSafetyError) as exc:
        print(f"Service Agent repair: FAIL\n  - {exc}")
        return 2
    return cmd_validate(argparse.Namespace(target=str(target)))

def cmd_validate(args) -> int:
    try:
        errors = validate_service_snapshot(load_snapshot(target_root(args.target)))
    except Exception as exc:
        print(f"Service Agent validation: FAIL\n  - {exc}")
        return 1
    if errors:
        print("Service Agent validation: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Service Agent validation: VALID")
    return 0

def cmd_ready(args) -> int:
    try:
        ready, reasons = service_readiness_snapshot(load_snapshot(target_root(args.target)))
    except Exception as exc:
        print(f"Service Agent readiness: NOT READY\n  - {exc}")
        return 1
    if not ready:
        print("Service Agent readiness: NOT READY")
        for reason in reasons:
            print(f"  - {reason}")
        return 1
    print("Service Agent readiness: READY (SERVICE AGENT REINSTANTIABLE)")
    return 0

def cmd_recover(args) -> int:
    try:
        pack = build_service_recovery_pack(
            load_snapshot(target_root(args.target)), max_chars=args.max_chars
        )
    except Exception as exc:
        print(f"Service Agent recovery: FAIL\n  - {exc}")
        return 1
    sys.stdout.write(pack)
    return 0

def cmd_durable_audit(args) -> int:
    snapshot = load_snapshot(target_root(args.target))
    problems = validate_service_snapshot(snapshot)
    if problems:
        for item in problems:
            print("  - " + item)
        print("Durable Service Agent audit: FAIL")
        return 1
    if ".context/service-agent/state-integrity.json" not in snapshot:
        print("Durable Service Agent audit: LEGACY / NOT INITIALIZED")
        return 0
    print("Durable Service Agent audit: PASS")
    return 0


def cmd_working_index(args) -> int:
    files = load_snapshot(target_root(args.target))
    problems = verify_durable_state(files)
    if problems:
        print("Working index: FAIL: " + "; ".join(problems))
        return 1
    if INDEX not in files:
        print("Working index: NOT INITIALIZED")
        return 1
    sys.stdout.write(files[INDEX])
    return 0


def cmd_durable_plan(args) -> int:
    try:
        target = target_root(args.target)
        snapshot = load_snapshot(target)
        problems = validate_service_snapshot(snapshot)
        if problems:
            raise DurableStateError("; ".join(problems))
        if args.init:
            changes = sealed_changes(snapshot, first=True)
            label = "initialize sealed professional state"
        else:
            payload = json.loads(Path(args.event).read_text(encoding="utf-8"))
            changes = event_changes(snapshot, payload)
            label = f"record durable Service Agent event {payload.get('id')}"
        if not args.publish:
            print(json.dumps({"status": "PLAN_ONLY", "changed_paths": sorted(changes)}, indent=2))
            return 0
        if not args.expected_head:
            raise DurableStateError("--expected-head required for publication")
        meta = json.loads(snapshot[".context/capsule.json"])
        manifest = json.loads(snapshot[".context/manifest.json"])
        commit = publish_files(
            snapshot, changes, meta["repository"], manifest["agent_state_branch"],
            args.expected_head, message="service-agent: " + label,
        )
        print(json.dumps({"status": "PUBLISHED", "commit": commit, "changed_paths": sorted(changes)}, indent=2))
        return 0
    except (DurableStateError, OSError, ValueError, KeyError) as exc:
        print(f"Durable Service Agent operation: FAIL\n  - {exc}")
        return 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="servicectl", description="Service Agent Base lifecycle helper")
    sub = p.add_subparsers(dest="command", required=True)

    i = sub.add_parser("install")
    i.add_argument("--target", required=True)
    i.add_argument("--repository", required=True)
    i.add_argument("--branch", default="main")
    i.add_argument("--source-commit")
    i.add_argument("--agent-id", required=True)
    i.add_argument("--role", required=True)
    i.add_argument("--specialization", required=True)
    i.set_defaults(func=cmd_install)

    r = sub.add_parser("repair")
    r.add_argument("--target", required=True)
    r.add_argument("--repository", required=True)
    r.add_argument("--branch", required=True)
    r.add_argument("--source-commit")
    r.set_defaults(func=cmd_repair)

    v = sub.add_parser("validate")
    v.add_argument("--target", required=True)
    v.set_defaults(func=cmd_validate)

    rd = sub.add_parser("ready")
    rd.add_argument("--target", required=True)
    rd.set_defaults(func=cmd_ready)

    rc = sub.add_parser("recover")
    rc.add_argument("--target", required=True)
    rc.add_argument("--max-chars", type=int, default=50000)
    rc.set_defaults(func=cmd_recover)

    audit = sub.add_parser("durable-audit", help="validate optional durable state and coherence")
    audit.add_argument("--target", required=True)
    audit.set_defaults(func=cmd_durable_audit)

    plan = sub.add_parser("durable-plan", help="preview or atomically publish durable service state")
    plan.add_argument("--target", required=True)
    mode = plan.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init", action="store_true", help="explicitly initialize the durable state seal")
    mode.add_argument("--event", help="JSON evidence-backed event to append")
    plan.add_argument("--expected-head", help="exact expected GitHub branch HEAD SHA")
    plan.add_argument("--publish", action="store_true", help="publish one non-forced GitHub commit")
    plan.set_defaults(func=cmd_durable_plan)

    index = sub.add_parser("working-index", help="verify and print compact non-authoritative index")
    index.add_argument("--target", required=True)
    index.set_defaults(func=cmd_working_index)
    return p

def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))

if __name__ == "__main__":
    raise SystemExit(main())
