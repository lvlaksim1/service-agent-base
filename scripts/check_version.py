#!/usr/bin/env python3
"""Stable numeric Service Agent Base version and implementation-change gate."""
from __future__ import annotations
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from installer.service_agent import SERVICE_AGENT_BASE_VERSION, VERSION

def parse(value):
    if value == "1.0.0-dev":
        return (1, 0, 0)
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value):
        raise ValueError(f"not a numeric stable version: {value}")
    return tuple(int(x) for x in value.split("."))

def check():
    version = (ROOT / "SERVICE_AGENT_BASE_VERSION").read_text(encoding="utf-8").strip()
    new = parse(version)
    if version != SERVICE_AGENT_BASE_VERSION or VERSION != "2.0.0":
        raise ValueError("numeric source version mismatch")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("published Service Agent Base version is not numeric")
    base = os.environ.get("BASE_SHA", "")
    if base and base != "0"*40:
        old = subprocess.check_output(["git", "show", f"{base}:SERVICE_AGENT_BASE_VERSION"], cwd=ROOT, text=True).strip()
        changed = subprocess.check_output(["git", "diff", "--name-only", base, "HEAD", "--", "installer/", "schemas/", "service-agent-templates/"], cwd=ROOT, text=True).splitlines()
        if new < parse(old):
            raise ValueError("stable version regressed")
        if changed and new == parse(old):
            tag = subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{version}"], cwd=ROOT, text=True, capture_output=True)
            if tag.returncode == 0:
                raise ValueError("released product source changed without a version increment")

if __name__ == "__main__":
    try:
        check()
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"VERSION FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    print("VERSION PASS")
