# Service Agent Base

Generic persistent Service Agent substrate for bounded professional agents such as
Supervisor, Auditor, Specialist, and Agent Factory profiles.

## Product boundary

This repository owns the generic Service Agent identity, engagement boundary,
professional-memory model, templates, schemas, lifecycle tooling, and recovery contract.

It does not own:

- Context Capsule Core: `lvlaksim1/context-capsule`;
- Project Manager: `lvlaksim1/context-capsule-project-manager`;
- Supervisor profile/state: `lvlaksim1/supervisor`;
- Auditor profile/state: `lvlaksim1/project-manager-auditor`;
- provisioning: `lvlaksim1/repo-factory`.

## Migration provenance

Extracted without behavioral change from
`lvlaksim1/context-capsule@7aa1e697504e686b02a4d7f1539a157214d5e692`,
the exact Service Agent Base commit previously pinned by repo-factory.

## Installed provenance

New and repaired Service Agent installations record the exact Service Agent Base source coordinate
as `service_agent_base_commit` and
`provenance.service_agent_base = { repository, commit }`.

The historical `core_commit` field is retained only as a deprecated compatibility alias for the
same Service Agent Base commit. It does **not** mean Context Capsule Core. Legacy installed agents
without the explicit field remain valid and are enriched by an explicit `servicectl repair`.

## Stable versions and durable state

The current Service Agent Base release is **1.1.0** and new installations use
numeric capsule version **2.0.0**. All releases are stable, with exactly three
numbers and no prefixes or suffixes. Legacy installed identifiers
`1.0.0-dev` / `2.0.0-dev` remain readable for an explicit repair; new
installations never emit these labels.

The additive durable-state protocol provides an explicit, sealed snapshot,
append-only evidence records, a structured engagement/commitment ledger, and
a compact non-authoritative working index. It never grants target authority or
closes an obligation based on a release alone. See [spec/durable-state-v1.md](spec/durable-state-v1.md).

## CLI

```bash
python installer/servicectl.py install --target /repo --repository owner/name --branch main \
  --agent-id my-agent --role "Service Agent" --specialization "..." \
  --source-commit <exact-service-agent-base-sha>
python installer/servicectl.py validate --target /repo
python installer/servicectl.py ready --target /repo
python installer/servicectl.py recover --target /repo
```

```bash
python installer/servicectl.py durable-audit --target /repo
python installer/servicectl.py durable-plan --target /repo --init
python installer/servicectl.py durable-plan --target /repo --event /tmp/verified-event.json
python installer/servicectl.py durable-plan --target /repo --event /tmp/verified-event.json --expected-head <sha> --publish
python installer/servicectl.py working-index --target /repo
```
Plan mode does not publish. Publication requires a matching exact branch head
and a write-capable `GITHUB_TOKEN`; it writes one fast-forward GitHub commit.
