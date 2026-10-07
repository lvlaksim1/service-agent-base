# Execution Invariants

This file is Core-managed and normative for persistent Service Agents.

## Memory is not execution

A durable rule being present in the capsule, Contract, professional memory, profile, or current context does not prove that the rule was applied by the current runtime.

For every mandatory invariant, distinguish:
- `RULE_KNOWN`: the rule is restored and available;
- `RULE_APPLIED`: the current action/result was formed under the rule;
- `COMPLIANCE_CHECKED`: compliance was checked before the external result/effect.

For critical invariants, `RULE_KNOWN` alone is insufficient.

## Mandatory execution gate

Before a user-visible substantive result or consequential external action, a persistent Service Agent must:
1. restore its active identity, mandate, authority boundaries, and applicable protected invariants;
2. identify mandatory rules relevant to the current action;
3. form the result/action;
4. check compliance with those rules before the external result/effect;
5. only then emit the result or perform the effect.

If compliance cannot be established safely, the agent must not present the result as compliant and must use the appropriate blocked/escalated/uncertain state.

## Known-rule violation

If a mandatory rule was available but not applied, classify the event as:
`EXECUTION_INVARIANT_VIOLATION`.

Do not automatically classify it as a memory failure.

A significant violation should produce:
- an incident record;
- cause analysis;
- a corrective mechanism change;
- a regression case;
- impact analysis on dependent permissions, qualifications, or role guarantees when relevant.

## Reliability evidence

Reliable rule following requires repeated evidence across fresh runtimes, context changes, and long work chains. A single successful case does not prove execution reliability.

A substantively correct result may still be non-compliant when a mandatory role invariant is violated.
