"""Opt-in, evidence-bounded durable Service Agent state and non-authoritative index."""
from __future__ import annotations

import copy
import hashlib
import json
from urllib.parse import quote

EVENTS = ".context/service-agent/durable-events.json"
COMMITMENTS = ".context/service-agent/commitments.json"
SEAL = ".context/service-agent/state-integrity.json"
INDEX = ".context/current/working-index.json"

KINDS = {"verified-fact", "verified-release", "risk", "engagement", "owner-decision", "handoff"}
ACTIONS = {"open", "complete", "cancel", "invalidate", "supersede"}
TERMINAL = {"completed", "cancelled", "invalidated", "superseded"}


class DurableStateError(ValueError):
    pass


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse(files, path, default=None):
    if path not in files:
        return copy.deepcopy(default)
    try:
        result = json.loads(files[path])
    except (TypeError, json.JSONDecodeError) as exc:
        raise DurableStateError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(result, dict):
        raise DurableStateError(f"expected object in {path}")
    return result


def canonical_paths(files):
    manifest = parse(files, ".context/manifest.json")
    if not manifest:
        raise DurableStateError("missing service manifest")
    agent = manifest["agent"]
    paths = [
        agent[k] for k in ("identity", "mandate", "beliefs", "goals", "intentions",
                          "plans", "engagements")
    ]
    paths += [manifest["current"][k] for k in ("state", "blockers", "next")]
    paths += [manifest["latest_handoff"]]
    paths += manifest.get("profile_state", {}).get("mandatory", [])
    paths += [EVENTS, COMMITMENTS]
    if len(paths) != len(set(paths)) or any(not p.startswith(".context/") or ".." in p.split("/") for p in paths):
        raise DurableStateError("duplicate or unsafe canonical path")
    for path in paths:
        if path not in files:
            raise DurableStateError(f"missing canonical state: {path}")
    return paths


def verify_durable_state(files):
    errors = []
    if SEAL not in files:
        if EVENTS in files or COMMITMENTS in files or INDEX in files:
            return ["durable state files exist without integrity seal"]
        return []
    try:
        seal = parse(files, SEAL)
        if seal.get("schema") != "service-agent-state-seal-v1":
            raise DurableStateError("invalid state integrity schema")
        generation = seal.get("generation")
        if not isinstance(generation, int) or generation < 1:
            raise DurableStateError("invalid state generation")
        paths = canonical_paths(files)
        if seal.get("paths") != paths:
            raise DurableStateError("state integrity path list does not match manifest")
        if set(seal.get("digests", {})) != set(paths):
            raise DurableStateError("state integrity digest set mismatch")
        for path in paths:
            if seal["digests"][path] != digest(files[path]):
                errors.append(f"state integrity mismatch: {path}")
        events = parse(files, EVENTS)
        commitments = parse(files, COMMITMENTS)
        if events.get("schema") != "service-agent-events-v1" or not isinstance(events.get("events"), list):
            errors.append("invalid durable events registry")
        else:
            ids = [e.get("id") for e in events["events"] if isinstance(e, dict)]
            if len(ids) != len(set(ids)):
                errors.append("duplicate durable event id")
        if commitments.get("schema") != "service-agent-commitments-v1" or not isinstance(commitments.get("items"), dict):
            errors.append("invalid structured commitments registry")
        elif any(v.get("status") not in ({"active"} | TERMINAL) for v in commitments["items"].values() if isinstance(v, dict)):
            errors.append("invalid commitment lifecycle status")
        if INDEX in files:
            index = parse(files, INDEX)
            if index.get("generation") != generation or index.get("seal_digest") != digest(files[SEAL]):
                errors.append("working index does not match canonical state seal")
            elif index.get("active_ids") != sorted(k for k, v in commitments["items"].items() if v.get("status") == "active"):
                errors.append("working index omits active structured commitments")
            if index.get("legacy_engagements_must_be_read") is not True:
                errors.append("working index cannot replace legacy engagements")
    except (DurableStateError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def _index(files):
    seal = parse(files, SEAL)
    commitments = parse(files, COMMITMENTS)
    result = {
        "schema": "service-agent-working-index-v1",
        "generation": seal["generation"],
        "seal_digest": digest(files[SEAL]),
        "canonical_sources": seal["paths"],
        "active_ids": sorted(k for k, v in commitments["items"].items() if v["status"] == "active"),
        "legacy_engagements_must_be_read": True,
        "legacy_intentions_must_be_read": True,
        "freshness": "NOT_CHECKED",
    }
    value = canonical(result)
    if len(value) > 8192:
        raise DurableStateError("working index exceeds 8192 characters")
    return value


def sealed_changes(files, *, first=False):
    provisional = dict(files)
    if first and SEAL in provisional:
        raise DurableStateError("durable state is already initialized")
    if not first and SEAL not in provisional:
        raise DurableStateError("state must be initialized first")
    if not first:
        errors = verify_durable_state(provisional)
        if errors:
            raise DurableStateError("incoherent state: " + "; ".join(errors))
    if EVENTS not in provisional:
        provisional[EVENTS] = canonical({"schema": "service-agent-events-v1", "events": []})
    if COMMITMENTS not in provisional:
        provisional[COMMITMENTS] = canonical({"schema": "service-agent-commitments-v1", "items": {}})
    paths = canonical_paths(provisional)
    old = parse(provisional, SEAL, {})
    seal = {"schema": "service-agent-state-seal-v1",
            "generation": old.get("generation", 0) + 1,
            "paths": paths,
            "digests": {p: digest(provisional[p]) for p in paths}}
    provisional[SEAL] = canonical(seal)
    provisional[INDEX] = _index(provisional)
    return {k: v for k, v in provisional.items() if files.get(k) != v}


def event_changes(files, event):
    if not isinstance(event, dict):
        raise DurableStateError("event must be an object")
    if SEAL not in files:
        raise DurableStateError("initialize durable state before recording events")
    faults = verify_durable_state(files)
    if faults:
        raise DurableStateError("incoherent state: " + "; ".join(faults))
    event_id = event.get("id")
    kind = event.get("kind")
    summary = event.get("summary")
    evidence = event.get("evidence")
    if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128 or not all(c.isalnum() or c in "-_." for c in event_id):
        raise DurableStateError("invalid event id")
    if kind not in KINDS or not isinstance(summary, str) or not 12 <= len(summary) <= 1200:
        raise DurableStateError("invalid event kind or summary")
    if not isinstance(evidence, dict) or not isinstance(evidence.get("source"), str) or not evidence["source"].strip():
        raise DurableStateError("event requires concrete evidence.source")
    if not isinstance(evidence.get("reference"), str) or not evidence["reference"].strip():
        raise DurableStateError("event requires concrete evidence.reference")
    if not isinstance(evidence.get("verified_by"), str) or not evidence["verified_by"].strip():
        raise DurableStateError("event requires explicit evidence.verified_by")
    if kind == "owner-decision" and event.get("owner_confirmed") is not True:
        raise DurableStateError("owner decision needs explicit owner confirmation")
    ops = event.get("commitments", [])
    if not isinstance(ops, list):
        raise DurableStateError("commitments must be an array")
    provisional = dict(files)
    journal = parse(provisional, EVENTS)
    if any(entry.get("id") == event_id for entry in journal["events"]):
        raise DurableStateError("event id already recorded")
    ledger = parse(provisional, COMMITMENTS)
    recorded = {k: dict(v) for k, v in ledger["items"].items()}
    for op in ops:
        if not isinstance(op, dict):
            raise DurableStateError("invalid commitment operation")
        cid, action = op.get("id"), op.get("action")
        if not isinstance(cid, str) or not 1 <= len(cid) <= 128 or not all(c.isalnum() or c in "-_." for c in cid) or action not in ACTIONS:
            raise DurableStateError("invalid commitment id or action")
        if action == "open":
            if cid in recorded:
                raise DurableStateError(f"commitment id already exists: {cid}")
            statement = op.get("statement")
            if not isinstance(statement, str) or len(statement.strip()) < 12:
                raise DurableStateError("open requires substantive commitment statement")
            if not isinstance(op.get("owner"), str) or not op["owner"].strip():
                raise DurableStateError("commitment owner required")
            recorded[cid] = {"status": "active", "statement": statement,
                             "owner": op["owner"], "opened_by": event_id,
                             "requires_owner_acceptance": op.get("requires_owner_acceptance") is True}
        else:
            prior = recorded.get(cid)
            if not prior or prior["status"] != "active":
                raise DurableStateError(f"commitment is absent or terminal: {cid}")
            if not isinstance(op.get("reason"), str) or len(op["reason"].strip()) < 12:
                raise DurableStateError("terminal transition requires explicit reason")
            if prior.get("requires_owner_acceptance") and action == "complete" and not (kind == "owner-decision" and event.get("owner_confirmed") is True):
                raise DurableStateError("commitment requires confirmed owner acceptance")
            prior["status"] = {"complete": "completed", "cancel": "cancelled",
                               "invalidate": "invalidated", "supersede": "superseded"}[action]
            prior["closed_by"] = event_id
            prior["reason"] = op["reason"]
    journal["events"].append({k: copy.deepcopy(v) for k, v in event.items()})
    ledger["items"] = recorded
    provisional[EVENTS] = canonical(journal)
    provisional[COMMITMENTS] = canonical(ledger)
    return sealed_changes(provisional, first=False) if False else _reseal_after_validated(files, provisional)


def _reseal_after_validated(before, provisional):
    old = parse(before, SEAL)
    paths = canonical_paths(provisional)
    seal = {"schema": "service-agent-state-seal-v1", "generation": old["generation"] + 1,
            "paths": paths, "digests": {p: digest(provisional[p]) for p in paths}}
    provisional[SEAL] = canonical(seal)
    provisional[INDEX] = _index(provisional)
    return {p: v for p, v in provisional.items() if before.get(p) != v}


def external_change_plan(files, changes):
    """Plain deterministic list of file writes; commit to GitHub only as one ref update."""
    return [{"path": k, "content": v} for k, v in sorted(changes.items())]
