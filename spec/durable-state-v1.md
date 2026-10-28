# Service Agent Base 1.1.0 — durable state, events and working context

This is an **opt-in** extension to a persistent Service Agent, not a Project Manager
implementation. Target projects remain external and require explicitly granted
engagement authority. Nothing in a GitHub release, CI, source file or agent note
grants target write authority or owner acceptance.

## Numeric stable versions

Service Agent Base \`1.1.0\` is a stable release. New Service Agent capsules use
numeric format \`2.0.0\`; both formats are purely numeric. Historical installed
\`1.0.0-dev\` and \`2.0.0-dev\` remain accepted only for explicit migration.
Each new compatible feature increments the second component, fixes the third,
and incompatible changes the first. No version prefixes or suffixes.

## Durable files and authority

Only the Service Agent home repository is canonical for agent identity,
commitments and professional state. Optional files:

- \`.context/service-agent/durable-events.json\` — append-only event records.
- \`.context/service-agent/commitments.json\` — stable IDs and explicit
  transitions active -> completed/cancelled/invalidated/superseded.
- \`.context/service-agent/state-integrity.json\` — generation and SHA-256
  digests of canonical professional, current, handoff and mandatory profile
  state, plus the two registries.
- \`.context/current/working-index.json\` — **non-authoritative** discoverable
  pointers, active structured IDs, generation and seal digest. Legacy intentions
  and engagement text MUST still be read. 8192-character budget.

Old capsules without any durable files remain valid. An incomplete extension
fails validation, so no partially written event is treated as trustworthy.
Durable files are created through an explicit, reviewed initialization; no
default repair may silently seal unknown drift or invent owners/acceptance.

## Event discipline

An event has unique \`id\`, \`kind\`, substantive \`summary\`, and a
\`evidence\` object containing \`source\`, \`reference\`, and \`verified_by\`.
These are provenance assertions, not automatic proof. Accepted types:
\`verified-fact\`, \`verified-release\`, \`risk\`, \`engagement\`,
\`owner-decision\`, \`handoff\`. Owner decisions additionally require
\`owner_confirmed: true\`; callers must have an actual direct authority
basis. An event with a release alone cannot complete commitments requiring
owner acceptance.

Commitment operations include \`open\` with \`id\`, \`statement\`, \`owner\`,
and \`requires_owner_acceptance\`; terminal transitions need a reason. No
duplicate event, duplicate commitment, arbitrary deletion, or return from
terminal state. No automatic transcription of older unstructured obligations:
legacy documents remain canonical until reconciled.

## Lifecycle

\`durable-plan --init\` previews the extension; \`durable-plan --event file.json\`
previews one transition. \`--publish --expected-head SHA\` writes one
GitHub commit with a fast-forward-only ref update using an explicitly provided
write-capable GITHUB_TOKEN. Publication checks remote preimages for files
already present in the local snapshot. The target branch is the Service Agent
home state branch, not a target project branch.

Use \`durable-audit\` for integrity and \`working-index\` for compact discovery.
Changes to sealed canonical state outside the transaction cause a mismatch and
must be reconciled through a reviewed new generation. An index alone cannot
override any missing or conflicting authoritative file.

Freshness of external projects is separate: a Supervisor portfolio-specific
read-only audit compares current GitHub evidence with reviewed baselines;
a valid seal or successful publication does not imply fresh target facts.
