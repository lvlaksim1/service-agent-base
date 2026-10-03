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

## CLI

```bash
python installer/servicectl.py install --target /repo --repository owner/name --branch main \
  --agent-id my-agent --role "Service Agent" --specialization "..." \
  --source-commit <exact-service-agent-base-sha>
python installer/servicectl.py validate --target /repo
python installer/servicectl.py ready --target /repo
python installer/servicectl.py recover --target /repo
```
