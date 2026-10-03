# Minimal Service Agent Base v1

Status: development contract for Master Plan item 2.

## Purpose

The Service Agent Base is the smallest persistent-agent substrate intended to support future Supervisor, Auditor, Specialist Agent, and Agent Factory profiles.

It is intentionally **not** a generic replacement for the Project Manager profile.

## Fundamental distinction

A Project Manager owns continuing responsibility for one project.

A Service Agent owns its **professional identity and service capability**, while projects/repositories/systems it works on remain external targets handled through bounded engagements.

This gives the system two distinct persistent-agent archetypes:

- **Project Agent:** persistent responsibility for one project.
- **Service Agent:** persistent professional role serving one or more external targets.

## Minimal durable state

A Service Agent persists:

- stable `agent_id`;
- role and specialization;
- mandate;
- capabilities;
- limitations;
- principal/requester model;
- invocation contract;
- result contract;
- professional beliefs/goals/intentions/plans;
- active engagement ledger;
- professional semantic/procedural/episodic memory;
- compact current state.

## Engagement boundary

Every engagement specifies requester, objective, target, scope, authority grant, constraints, data-handling boundary, and deliverable.

The base profile defaults to advisory output and requires explicit grant for target-side action.

Repository access and tool capability are never treated as authority.

## Memory boundary

Target context is engagement-scoped. Durable memory is professional.

The agent may generalize safe reusable lessons, but must not silently copy target secrets/state into professional memory or reuse one target's context for another target.

## Lifecycle

`Reinstate → Validate Invocation → Acquire Scoped Context → Plan → Execute/Analyze → Verify → Deliver → Reflect → Persist`

Active engagements survive runtime replacement.

## Profile-specific durable state

Profiles may register additional durable files through `manifest.profile_state`:

- `mandatory` — role-specific state required in every reinstantiation pack;
- `optional` — deeper role-specific state that may be omitted under recovery budget pressure and retrieved later.

This lets Supervisor keep portfolio registries, Auditor keep audit control state, and future profiles add their own durable surfaces without changing the universal Service Agent identity model.

Profile-state files remain subject to the Service Agent authority and target-isolation guarantees.

## Profiles

Future profiles extend the base:

- Supervisor: portfolio coordination under owner authority.
- Auditor: independent verification, normally read-only.
- Specialist: narrow domain expertise.
- Agent Factory: designs and provisions missing specialist roles.

A profile may specialize authority and outputs but cannot silently remove stable identity, target isolation, explicit engagement authority, professional-memory isolation, or self-authority restrictions.

## Installation surface

The development CLI exposes:

- `service-install`
- `service-repair`
- `service-validate`
- `service-ready`
- `service-recover`

The Service Agent profile is stored under the same repository-local `.context/` root but uses a distinct manifest/identity schema from Project Manager v2.

## Why this is separate rather than a premature universal Agent Core

Project Manager and Service Agent now demonstrate two different ownership models. Their common substrate may later justify a more general Agent Core, but that generalization is intentionally deferred until real Supervisor/Auditor/Specialist profiles exist.
