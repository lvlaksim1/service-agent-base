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
    return p

def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))

if __name__ == "__main__":
    raise SystemExit(main())
