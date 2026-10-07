from __future__ import annotations

import copy
import datetime as dt
import json
import re
from pathlib import Path

from .safety import CapsuleSafetyError, normalize_repo_path, render_managed_block, validate_core_commit
VERSION = "2.0.0-dev"

SERVICE_AGENT_BASE_VERSION = "1.0.0-dev"
SERVICE_AGENT_BASE_REPOSITORY = "lvlaksim1/service-agent-base"
SERVICE_AGENT_IDENTITY_SCHEMA_VERSION = 1
SERVICE_AGENT_MANIFEST_SCHEMA_VERSION = 1
SERVICE_IDENTITY_PATH = ".context/service-agent/identity.json"

SERVICE_SYSTEM_PATHS = (
    ".context/ENTRYPOINT.md",
    ".context/EXECUTION_INVARIANTS.md",
    ".context/service-agent/CONTRACT.md",
    ".context/service-agent/PROTOCOL.md",
)

SERVICE_SEED_PATHS = (
    ".context/service-agent/mandate.md",
    ".context/service-agent/capabilities.md",
    ".context/service-agent/limitations.md",
    ".context/service-agent/principal-model.md",
    ".context/service-agent/invocation-contract.md",
    ".context/service-agent/result-contract.md",
    ".context/service-agent/beliefs.md",
    ".context/service-agent/goals.md",
    ".context/service-agent/intentions.md",
    ".context/service-agent/plans.md",
    ".context/service-agent/engagements.md",
    ".context/current/state.md",
    ".context/current/blockers.md",
    ".context/current/next.md",
    ".context/memory/index.md",
    ".context/memory/semantic.md",
    ".context/memory/procedural.md",
    ".context/memory/episodes/README.md",
    ".context/handoffs/latest.md",
)

SERVICE_BOOTSTRAP_FILES = ("AI_CONTEXT.md", "AGENTS.md")
_AGENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")

_PLACEHOLDER_PATTERNS = (
    "define the service agent",
    "record the service agent",
    "record durable professional",
    "record active service commitments",
    "record the current service plan",
    "record active engagements",
    "capture current verified",
    "capture current blockers",
    "capture next actions",
    "no handoff recorded yet",
)


class ServiceAgentModelError(ValueError):
    pass


def _canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def _load_template(template_root: Path, rel: str) -> str:
    path = template_root / rel
    if not path.exists():
        raise ServiceAgentModelError(f"missing Service Agent template: {rel}")
    return path.read_text(encoding="utf-8")


def _parse_json(files: dict[str, str], path: str) -> dict | None:
    text = files.get(path)
    if text is None:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ServiceAgentModelError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ServiceAgentModelError(f"JSON root must be an object: {path}")
    return value


def _bootstrap_changes(files: dict[str, str], template_root: Path) -> dict[str, str]:
    return {
        "AI_CONTEXT.md": render_managed_block(
            files.get("AI_CONTEXT.md"),
            _load_template(template_root, "AI_CONTEXT.md").strip(),
            default_heading="# AI Context",
        ),
        "AGENTS.md": render_managed_block(
            files.get("AGENTS.md"),
            _load_template(template_root, "AGENTS.md").strip(),
            default_heading="# Agent Instructions",
        ),
    }


def build_service_agent_identity(
    repository: str,
    agent_id: str,
    role: str,
    specialization: str,
    *,
    existing: dict | None = None,
) -> dict:
    if not _AGENT_ID.fullmatch(agent_id):
        raise ServiceAgentModelError("agent_id must be a stable 3-128 character identifier")
    if not role.strip():
        raise ServiceAgentModelError("role must be non-empty")
    if not specialization.strip():
        raise ServiceAgentModelError("specialization must be non-empty")
    result = copy.deepcopy(existing or {})
    result.update(
        {
            "schema": "context-capsule-service-agent-identity",
            "schema_version": SERVICE_AGENT_IDENTITY_SCHEMA_VERSION,
            "agent_id": result.get("agent_id") or agent_id,
            "agent_type": "service-agent",
            "role": result.get("role") or role,
            "specialization": result.get("specialization") or specialization,
            "repository": repository,
            "continuity": "runtime-independent",
            "ownership_model": "home-repository-not-client-target",
            "authority_model": "bounded-by-mandate-and-engagement",
            "memory_model": "professional-with-target-isolation",
        }
    )
    return result


def build_service_manifest(repository: str, branch: str, *, existing: dict | None = None) -> dict:
    manifest = copy.deepcopy(existing or {})
    agent = copy.deepcopy(manifest.get("agent") if isinstance(manifest.get("agent"), dict) else {})
    agent.update(
        {
            "contract": ".context/service-agent/CONTRACT.md",
            "protocol": ".context/service-agent/PROTOCOL.md",
            "identity": SERVICE_IDENTITY_PATH,
            "mandate": ".context/service-agent/mandate.md",
            "capabilities": ".context/service-agent/capabilities.md",
            "limitations": ".context/service-agent/limitations.md",
            "principal_model": ".context/service-agent/principal-model.md",
            "invocation_contract": ".context/service-agent/invocation-contract.md",
            "result_contract": ".context/service-agent/result-contract.md",
            "beliefs": ".context/service-agent/beliefs.md",
            "goals": ".context/service-agent/goals.md",
            "intentions": ".context/service-agent/intentions.md",
            "plans": ".context/service-agent/plans.md",
            "engagements": ".context/service-agent/engagements.md",
        }
    )
    current = copy.deepcopy(manifest.get("current") if isinstance(manifest.get("current"), dict) else {})
    current.update(
        {
            "state": ".context/current/state.md",
            "blockers": ".context/current/blockers.md",
            "next": ".context/current/next.md",
        }
    )
    memory = copy.deepcopy(manifest.get("memory") if isinstance(manifest.get("memory"), dict) else {})
    memory.update(
        {
            "index": ".context/memory/index.md",
            "semantic": ".context/memory/semantic.md",
            "procedural": ".context/memory/procedural.md",
            "episodes": memory.get("episodes") if isinstance(memory.get("episodes"), list) else [],
        }
    )
    profile_state = copy.deepcopy(
        manifest.get("profile_state") if isinstance(manifest.get("profile_state"), dict) else {}
    )
    profile_state.update(
        {
            "mandatory": (
                profile_state.get("mandatory")
                if isinstance(profile_state.get("mandatory"), list)
                else []
            ),
            "optional": (
                profile_state.get("optional")
                if isinstance(profile_state.get("optional"), list)
                else []
            ),
        }
    )
    manifest.update(
        {
            "schema": "context-capsule-service-agent-manifest",
            "schema_version": SERVICE_AGENT_MANIFEST_SCHEMA_VERSION,
            "profile": "service-agent",
            "profile_version": SERVICE_AGENT_BASE_VERSION,
            "repository": repository,
            "agent_state_branch": branch,
            "entrypoint": ".context/ENTRYPOINT.md",
            "capsule_metadata": ".context/capsule.json",
            "latest_handoff": ".context/handoffs/latest.md",
            "agent": agent,
            "current": current,
            "memory": memory,
            "profile_state": profile_state,
            "runtime": {
                "checkpoint_is_capsule_state": False,
            },
            "sync_policy": {
                "semantic_only": True,
                "professional_memory_only": True,
                "target_context_isolated": True,
                "target_authority_requires_explicit_grant": True,
                "service_output_advisory_by_default": True,
                "authority_transport_non_escalating": True,
                "self_authority_expansion_forbidden": True,
            },
            "updated_at": dt.date.today().isoformat(),
        }
    )
    return manifest


def _metadata(repository: str, core_commit: str, *, existing: dict | None = None) -> dict:
    # Historical internal name core_commit carries the Service Agent Base source
    # commit. Keep it as a compatibility alias, but expose the semantic coordinate.
    service_agent_base_commit = validate_core_commit(core_commit)
    result = copy.deepcopy(existing or {})
    result.update(
        {
            "schema": "context-capsule",
            "version": VERSION,
            "profile": "service-agent",
            "profile_version": SERVICE_AGENT_BASE_VERSION,
            "source": SERVICE_AGENT_BASE_REPOSITORY,
            "core_commit": service_agent_base_commit,
            "service_agent_base_commit": service_agent_base_commit,
            "provenance": {
                "service_agent_base": {
                    "repository": SERVICE_AGENT_BASE_REPOSITORY,
                    "commit": service_agent_base_commit,
                }
            },
            "installed_at": result.get("installed_at") or dt.date.today().isoformat(),
            "repository": repository,
            "update_policy": "manual",
        }
    )
    return result


def _seed_structure(
    provisional: dict[str, str],
    template_root: Path,
    repository: str,
    agent_id: str,
    role: str,
    specialization: str,
    *,
    overwrite_system: bool,
) -> None:
    for rel in SERVICE_SYSTEM_PATHS:
        if overwrite_system or rel not in provisional:
            provisional[rel] = _load_template(template_root, rel)
    for rel in SERVICE_SEED_PATHS:
        if rel not in provisional:
            provisional[rel] = _load_template(template_root, rel)

    existing = None
    if SERVICE_IDENTITY_PATH in provisional:
        try:
            existing = json.loads(provisional[SERVICE_IDENTITY_PATH])
        except Exception:
            existing = None
    provisional[SERVICE_IDENTITY_PATH] = _canonical_json(
        build_service_agent_identity(
            repository,
            agent_id,
            role,
            specialization,
            existing=existing if isinstance(existing, dict) else None,
        )
    )


def service_clean_install_changes(
    files: dict[str, str],
    template_root: Path,
    repository: str,
    branch: str,
    core_commit: str,
    agent_id: str,
    role: str,
    specialization: str,
    *,
    semantic_overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    if any(path == ".context" or path.startswith(".context/") for path in files):
        raise ServiceAgentModelError("service-agent clean install refused: existing .context content found")
    validate_core_commit(core_commit)
    provisional = dict(files)
    provisional.update(_bootstrap_changes(files, template_root))
    _seed_structure(
        provisional,
        template_root,
        repository,
        agent_id,
        role,
        specialization,
        overwrite_system=True,
    )
    if semantic_overrides:
        for raw_path, content in semantic_overrides.items():
            path = normalize_repo_path(raw_path)
            if not path.startswith(".context/"):
                raise ServiceAgentModelError(f"semantic override must be inside .context/: {path}")
            provisional[path] = content
    provisional[".context/capsule.json"] = _canonical_json(_metadata(repository, core_commit))
    provisional[".context/manifest.json"] = _canonical_json(build_service_manifest(repository, branch))
    errors = validate_service_snapshot(provisional)
    if errors:
        raise ServiceAgentModelError("planned service-agent install is invalid: " + "; ".join(errors))
    return {path: provisional[path] for path in provisional if files.get(path) != provisional[path]}


def service_repair_changes(
    files: dict[str, str],
    template_root: Path,
    repository: str,
    branch: str,
    core_commit: str,
) -> dict[str, str]:
    meta = _parse_json(files, ".context/capsule.json") or {}
    manifest = _parse_json(files, ".context/manifest.json") or {}
    identity = _parse_json(files, SERVICE_IDENTITY_PATH) or {}
    if meta.get("version") != VERSION or meta.get("profile") != "service-agent":
        raise ServiceAgentModelError("service-agent repair requires an installed v2 service-agent profile")
    if manifest.get("agent_state_branch") != branch:
        raise ServiceAgentModelError(
            f"service-agent repair must run against agent state branch {manifest.get('agent_state_branch')!r}"
        )
    provisional = dict(files)
    provisional.update(_bootstrap_changes(files, template_root))
    _seed_structure(
        provisional,
        template_root,
        repository,
        identity.get("agent_id", "service-agent"),
        identity.get("role", "Service Agent"),
        identity.get("specialization", "General service"),
        overwrite_system=True,
    )
    provisional[".context/capsule.json"] = _canonical_json(_metadata(repository, core_commit, existing=meta))
    provisional[".context/manifest.json"] = _canonical_json(
        build_service_manifest(repository, branch, existing=manifest)
    )
    errors = validate_service_snapshot(provisional)
    if errors:
        raise ServiceAgentModelError("planned service-agent repair is invalid: " + "; ".join(errors))
    return {path: provisional[path] for path in provisional if files.get(path) != provisional[path]}


def _service_references(manifest: dict) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    for key in ("entrypoint", "capsule_metadata", "latest_handoff"):
        value = manifest.get(key)
        if isinstance(value, str):
            refs.append((key, value))
    for section in ("agent", "current"):
        value = manifest.get(section)
        if isinstance(value, dict):
            for key, path in value.items():
                if isinstance(path, str):
                    refs.append((f"{section}.{key}", path))
    memory = manifest.get("memory")
    if isinstance(memory, dict):
        for key in ("index", "semantic", "procedural"):
            path = memory.get(key)
            if isinstance(path, str):
                refs.append((f"memory.{key}", path))
        episodes = memory.get("episodes")
        if isinstance(episodes, list):
            for index, path in enumerate(episodes):
                if isinstance(path, str):
                    refs.append((f"memory.episodes[{index}]", path))
    profile_state = manifest.get("profile_state")
    if isinstance(profile_state, dict):
        for bucket in ("mandatory", "optional"):
            paths = profile_state.get(bucket)
            if isinstance(paths, list):
                for index, path in enumerate(paths):
                    if isinstance(path, str):
                        refs.append((f"profile_state.{bucket}[{index}]", path))
    return refs


def validate_service_snapshot(files: dict[str, str]) -> list[str]:
    errors: list[str] = []
    try:
        meta = _parse_json(files, ".context/capsule.json")
    except ServiceAgentModelError as exc:
        errors.append(str(exc))
        meta = None
    try:
        manifest = _parse_json(files, ".context/manifest.json")
    except ServiceAgentModelError as exc:
        errors.append(str(exc))
        manifest = None

    if meta is None:
        errors.append("missing .context/capsule.json")
    else:
        if meta.get("schema") != "context-capsule":
            errors.append("capsule.json: invalid schema")
        if meta.get("version") != VERSION:
            errors.append(f"capsule.json: version must be {VERSION}")
        if meta.get("profile") != "service-agent":
            errors.append("capsule.json: profile must be service-agent")
        if meta.get("profile_version") != SERVICE_AGENT_BASE_VERSION:
            errors.append(f"capsule.json: profile_version must be {SERVICE_AGENT_BASE_VERSION}")
        provenance = meta.get("provenance")
        if isinstance(provenance, dict):
            service_base = provenance.get("service_agent_base")
            if (
                not isinstance(service_base, dict)
                or service_base.get("repository") != SERVICE_AGENT_BASE_REPOSITORY
            ):
                errors.append("capsule.json: provenance.service_agent_base.repository is invalid")
            try:
                source_commit = validate_core_commit(
                    service_base.get("commit", "") if isinstance(service_base, dict) else ""
                )
                if meta.get("service_agent_base_commit") not in (None, source_commit):
                    errors.append("capsule.json: service_agent_base_commit disagrees with provenance")
                if meta.get("core_commit") not in (None, source_commit):
                    errors.append("capsule.json: deprecated core_commit alias disagrees with Service Agent Base provenance")
            except CapsuleSafetyError as exc:
                errors.append(f"capsule.json: {exc}")
        else:
            try:
                validate_core_commit(meta.get("service_agent_base_commit") or meta.get("core_commit", ""))
            except CapsuleSafetyError as exc:
                errors.append(f"capsule.json: {exc}")
        if not isinstance(meta.get("repository"), str) or meta["repository"].count("/") != 1:
            errors.append("capsule.json: repository must be owner/name")
        if meta.get("update_policy") != "manual":
            errors.append("capsule.json: update_policy must be manual")

    for path in SERVICE_SYSTEM_PATHS:
        if path not in files:
            errors.append(f"missing service-agent system file: {path}")
    for path in SERVICE_BOOTSTRAP_FILES:
        if path not in files:
            errors.append(f"missing bootstrap file: {path}")

    if manifest is None:
        errors.append("missing .context/manifest.json")
    else:
        if manifest.get("schema") != "context-capsule-service-agent-manifest":
            errors.append("manifest.json: invalid service-agent schema")
        if manifest.get("schema_version") != SERVICE_AGENT_MANIFEST_SCHEMA_VERSION:
            errors.append(
                f"manifest.json: schema_version must be {SERVICE_AGENT_MANIFEST_SCHEMA_VERSION}"
            )
        if manifest.get("profile") != "service-agent":
            errors.append("manifest.json: profile must be service-agent")
        if manifest.get("profile_version") != SERVICE_AGENT_BASE_VERSION:
            errors.append(f"manifest.json: profile_version must be {SERVICE_AGENT_BASE_VERSION}")
        if meta and manifest.get("repository") != meta.get("repository"):
            errors.append("manifest.json repository does not match capsule.json")
        if not isinstance(manifest.get("agent_state_branch"), str) or not manifest.get("agent_state_branch"):
            errors.append("manifest.json: agent_state_branch is required")

        for label, raw_path in _service_references(manifest):
            try:
                path = normalize_repo_path(raw_path)
            except CapsuleSafetyError as exc:
                errors.append(f"manifest.json {label}: {exc}")
                continue
            if path not in files:
                errors.append(f"manifest.json {label}: referenced path does not exist: {path}")

        sync = manifest.get("sync_policy")
        required_flags = {
            "semantic_only": "semantic-only persistence must be enabled",
            "professional_memory_only": "service memory must remain professional memory",
            "target_context_isolated": "target context isolation must be enabled",
            "target_authority_requires_explicit_grant": "target authority requires explicit grant",
            "service_output_advisory_by_default": "service output must be advisory by default",
            "authority_transport_non_escalating": "authority must not escalate through transport",
            "self_authority_expansion_forbidden": "service agent must not self-expand authority",
        }
        for key, message in required_flags.items():
            if not isinstance(sync, dict) or sync.get(key) is not True:
                errors.append(f"manifest.json: {message}")

        profile_state = manifest.get("profile_state")
        if not isinstance(profile_state, dict):
            errors.append("manifest.json: profile_state object is required")
        else:
            for bucket in ("mandatory", "optional"):
                paths = profile_state.get(bucket)
                if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
                    errors.append(f"manifest.json: profile_state.{bucket} must be a list of paths")

        runtime = manifest.get("runtime")
        if not isinstance(runtime, dict) or runtime.get("checkpoint_is_capsule_state") is not False:
            errors.append("manifest.json: runtime checkpoint must remain separate from service-agent state")

    try:
        identity = _parse_json(files, SERVICE_IDENTITY_PATH)
    except ServiceAgentModelError as exc:
        errors.append(str(exc))
        identity = None
    if identity is None:
        errors.append(f"missing {SERVICE_IDENTITY_PATH}")
    else:
        if identity.get("schema") != "context-capsule-service-agent-identity":
            errors.append("service-agent identity: invalid schema")
        if identity.get("schema_version") != SERVICE_AGENT_IDENTITY_SCHEMA_VERSION:
            errors.append(
                f"service-agent identity: schema_version must be {SERVICE_AGENT_IDENTITY_SCHEMA_VERSION}"
            )
        if not isinstance(identity.get("agent_id"), str) or not _AGENT_ID.fullmatch(identity["agent_id"]):
            errors.append("service-agent identity: invalid agent_id")
        if identity.get("agent_type") != "service-agent":
            errors.append("service-agent identity: agent_type must be service-agent")
        if not isinstance(identity.get("role"), str) or not identity["role"].strip():
            errors.append("service-agent identity: role must be non-empty")
        if not isinstance(identity.get("specialization"), str) or not identity["specialization"].strip():
            errors.append("service-agent identity: specialization must be non-empty")
        if identity.get("continuity") != "runtime-independent":
            errors.append("service-agent identity: continuity must be runtime-independent")
        if identity.get("ownership_model") != "home-repository-not-client-target":
            errors.append("service-agent identity: target ownership boundary is invalid")
        if meta and identity.get("repository") != meta.get("repository"):
            errors.append("service-agent identity repository does not match capsule repository")

    return errors


def _semantic_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("<!--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _is_substantive(text: str | None) -> bool:
    if text is None:
        return False
    body = _semantic_text(text)
    if len(body) < 32:
        return False
    lower = body.lower()
    return not any(lower.startswith(pattern) for pattern in _PLACEHOLDER_PATTERNS)


def _has_provenance(text: str | None) -> bool:
    return _is_substantive(text) and "source:" in text.lower() and "authority:" in text.lower()


def service_readiness_snapshot(files: dict[str, str]) -> tuple[bool, list[str]]:
    errors = validate_service_snapshot(files)
    if errors:
        return False, [f"VALIDATION: {item}" for item in errors]
    manifest = _parse_json(files, ".context/manifest.json") or {}
    agent = manifest["agent"]
    required = {
        "agent.mandate": agent["mandate"],
        "agent.capabilities": agent["capabilities"],
        "agent.limitations": agent["limitations"],
        "agent.principal_model": agent["principal_model"],
        "agent.invocation_contract": agent["invocation_contract"],
        "agent.result_contract": agent["result_contract"],
        "agent.goals": agent["goals"],
        "agent.intentions": agent["intentions"],
        "agent.plans": agent["plans"],
        "agent.engagements": agent["engagements"],
        "current.state": manifest["current"]["state"],
        "current.next": manifest["current"]["next"],
    }
    missing: list[str] = []
    for label, path in required.items():
        if not _is_substantive(files.get(path)):
            missing.append(f"{label} is empty or still a template")
    if not _has_provenance(files.get(agent["beliefs"])):
        missing.append("agent.beliefs must be substantive and include source: and authority: provenance")
    return not missing, missing


def build_service_recovery_pack(files: dict[str, str], *, max_chars: int = 50000) -> str:
    ready, reasons = service_readiness_snapshot(files)
    if not ready:
        raise ServiceAgentModelError("service agent is not READY: " + "; ".join(reasons))
    manifest = _parse_json(files, ".context/manifest.json") or {}
    agent = manifest["agent"]
    identity = _parse_json(files, agent["identity"]) or {}

    mandatory = [
        ("EXECUTION INVARIANTS", ".context/EXECUTION_INVARIANTS.md"),
        ("SERVICE AGENT CONTRACT", agent["contract"]),
        ("SERVICE AGENT PROTOCOL", agent["protocol"]),
        ("SERVICE AGENT IDENTITY", agent["identity"]),
        ("SERVICE AGENT MANDATE", agent["mandate"]),
        ("SERVICE AGENT CAPABILITIES", agent["capabilities"]),
        ("SERVICE AGENT LIMITATIONS", agent["limitations"]),
        ("PRINCIPAL MODEL", agent["principal_model"]),
        ("INVOCATION CONTRACT", agent["invocation_contract"]),
        ("RESULT CONTRACT", agent["result_contract"]),
        ("SERVICE BELIEFS", agent["beliefs"]),
        ("SERVICE GOALS", agent["goals"]),
        ("SERVICE INTENTIONS", agent["intentions"]),
        ("SERVICE PLANS", agent["plans"]),
        ("ACTIVE ENGAGEMENTS", agent["engagements"]),
        ("CURRENT STATE", manifest["current"]["state"]),
        ("NEXT ACTIONS", manifest["current"]["next"]),
    ]
    for path in manifest.get("profile_state", {}).get("mandatory", []):
        mandatory.append(("PROFILE STATE", path))

    optional = [
        ("CURRENT BLOCKERS", manifest["current"]["blockers"]),
        ("PROFESSIONAL SEMANTIC MEMORY", manifest["memory"]["semantic"]),
        ("PROFESSIONAL PROCEDURAL MEMORY", manifest["memory"]["procedural"]),
        ("LATEST HANDOFF", manifest["latest_handoff"]),
    ]
    for path in manifest.get("profile_state", {}).get("optional", []):
        optional.append(("OPTIONAL PROFILE STATE", path))
    for path in manifest["memory"].get("episodes", []):
        optional.append(("PROFESSIONAL EPISODE", path))

    chunks = [
        "# CONTEXT CAPSULE SERVICE AGENT REINSTANTIATION PACK",
        "",
        f"Repository: {manifest.get('repository')}",
        f"Agent state branch: {manifest.get('agent_state_branch')}",
        f"Agent ID: {identity.get('agent_id')}",
        f"Role: {identity.get('role')}",
        f"Specialization: {identity.get('specialization')}",
        "",
        "You are a new runtime instance of the existing Service Agent, not a new agent.",
        "The home repository owns this agent's identity and professional memory. Client/target repositories do not become this agent's owned project state.",
        "Every target action requires the authority granted by the current engagement; repository access or tool capability is not permission.",
        "",
    ]
    used = sum(len(x) + 1 for x in chunks)
    for label, path in mandatory:
        text = files.get(path)
        if text is None:
            continue
        chunk = f"## {label}: {path}\n\n{text.strip()}\n"
        if used + len(chunk) > max_chars:
            raise ServiceAgentModelError(
                f"recovery budget too small for mandatory service-agent state: {path}"
            )
        chunks.append(chunk)
        used += len(chunk)

    omitted: list[str] = []
    for label, path in optional:
        text = files.get(path)
        if text is None:
            continue
        chunk = f"## {label}: {path}\n\n{text.strip()}\n"
        if used + len(chunk) > max_chars:
            omitted.append(path)
            continue
        chunks.append(chunk)
        used += len(chunk)
    if omitted:
        chunks.append("## OMITTED DEEPER PROFESSIONAL MEMORY\n\n" + "\n".join(f"- {p}" for p in omitted))
    return "\n".join(chunks).rstrip() + "\n"
