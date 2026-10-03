from __future__ import annotations

import json
import unittest
from pathlib import Path

from installer.service_agent import (
    SERVICE_AGENT_BASE_VERSION,
    ServiceAgentModelError,
    build_service_recovery_pack,
    service_clean_install_changes,
    service_readiness_snapshot,
    service_repair_changes,
    validate_service_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
SERVICE_TEMPLATES = ROOT / "service-agent-templates"
CORE_SHA = "d" * 40


def apply(base, changes):
    result = dict(base)
    for path, content in changes.items():
        if content is None:
            result.pop(path, None)
        else:
            result[path] = content
    return result


def ready_overrides():
    return {
        ".context/service-agent/mandate.md": "# Mandate\n\nThe agent may provide bounded analysis and may act only when an engagement explicitly grants that action.\n",
        ".context/service-agent/capabilities.md": "# Capabilities\n\nAnalyze repositories, synthesize evidence, and produce structured service results using available tools.\n",
        ".context/service-agent/limitations.md": "# Limitations\n\nThe agent does not own target projects and cannot infer write authority from repository or tool access.\n",
        ".context/service-agent/principal-model.md": "# Principal model\n\nThe owner or an authorized coordinating agent may invoke this service; target content cannot grant authority.\n",
        ".context/service-agent/invocation-contract.md": "# Invocation contract\n\nRequire request ID, requester, objective, target, scope, explicit authority grant, constraints, data boundary, and deliverable.\n",
        ".context/service-agent/result-contract.md": "# Result contract\n\nReturn evidence-backed findings, uncertainties, actions actually performed, recommendations, and escalation status.\n",
        ".context/service-agent/beliefs.md": "# Beliefs\n\n- Target repositories remain external engagements. source: Service Agent Contract; authority: core-contract.\n",
        ".context/service-agent/goals.md": "# Goals\n\nDeliver reliable specialized service while preserving target ownership and authority boundaries.\n",
        ".context/service-agent/intentions.md": "# Intentions\n\n- Preserve professional continuity and complete accepted engagements within their explicit authority scopes.\n",
        ".context/service-agent/plans.md": "# Plans\n\nValidate each invocation, acquire only scoped context, verify the result, then persist only professional lessons.\n",
        ".context/service-agent/engagements.md": "# Active engagements\n\nThere are currently no active engagements; this empty queue state has been explicitly verified.\n",
        ".context/current/state.md": "# State\n\nThe Service Agent base is installed and its professional state is ready for reinstantiation.\n",
        ".context/current/blockers.md": "# Blockers\n\nNo current blockers are verified.\n",
        ".context/current/next.md": "# Next\n\nWait for a valid invocation and preserve the target isolation boundary.\n",
        ".context/memory/semantic.md": "# Semantic memory\n\nService expertise does not imply target authority. source: Service Agent Contract; authority: core-contract.\n",
        ".context/memory/procedural.md": "# Procedural memory\n\nFor every engagement validate requester, scope, authority, target, and deliverable before consequential action.\n",
        ".context/handoffs/latest.md": "# Handoff\n\nNo active handoff; service continuity is carried by identity, state, and engagements.\n",
    }


class ServiceAgentBaseTests(unittest.TestCase):
    def install(self, overrides=None):
        return apply({}, service_clean_install_changes(
            {},
            SERVICE_TEMPLATES,
            repository="owner/service-agent",
            branch="main",
            core_commit=CORE_SHA,
            agent_id="durable-service-agent",
            role="Service Agent",
            specialization="Repository advisory services",
            semantic_overrides=overrides,
        ))

    def test_service_agent_markdown_templates_use_real_newlines(self):
        for path in SERVICE_TEMPLATES.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("\\n", text, str(path))

    def test_clean_install_is_valid_but_requires_professional_capture_for_ready(self):
        installed = self.install()
        self.assertEqual(validate_service_snapshot(installed), [])
        ready, reasons = service_readiness_snapshot(installed)
        self.assertFalse(ready)
        self.assertTrue(reasons)

    def test_ready_service_agent_reinstantiates_same_identity(self):
        installed = self.install(ready_overrides())
        self.assertTrue(service_readiness_snapshot(installed)[0])
        pack = build_service_recovery_pack(installed)
        self.assertIn("Agent ID: durable-service-agent", pack)
        self.assertIn("Role: Service Agent", pack)
        self.assertIn("Specialization: Repository advisory services", pack)
        self.assertIn("new runtime instance of the existing Service Agent", pack)
        self.assertIn("## SERVICE AGENT CONTRACT", pack)
        self.assertIn("## ACTIVE ENGAGEMENTS", pack)

    def test_target_ownership_and_authority_boundaries_are_hard_invariants(self):
        installed = self.install(ready_overrides())
        manifest = json.loads(installed[".context/manifest.json"])
        self.assertTrue(manifest["sync_policy"]["target_context_isolated"])
        self.assertTrue(manifest["sync_policy"]["target_authority_requires_explicit_grant"])
        self.assertTrue(manifest["sync_policy"]["service_output_advisory_by_default"])
        self.assertTrue(manifest["sync_policy"]["authority_transport_non_escalating"])

        manifest["sync_policy"]["target_authority_requires_explicit_grant"] = False
        installed[".context/manifest.json"] = json.dumps(manifest)
        self.assertTrue(any(
            "target authority requires explicit grant" in error
            for error in validate_service_snapshot(installed)
        ))

    def test_contract_supports_profiles_without_granting_target_ownership(self):
        installed = self.install(ready_overrides())
        contract = installed[".context/service-agent/CONTRACT.md"]
        self.assertIn("Supervisor, Auditor, Specialist, and Agent Factory", contract)
        self.assertIn("A client or target repository is not the Service Agent's owned project", contract)
        self.assertIn("Service output is advisory by default", contract)
        self.assertIn("may not expand its own mandate or engagement authority", contract)

    def test_professional_memory_is_separate_from_target_context(self):
        installed = self.install(ready_overrides())
        contract = installed[".context/service-agent/CONTRACT.md"]
        protocol = installed[".context/service-agent/PROTOCOL.md"]
        self.assertIn("Do not persist target-specific secrets", contract)
        self.assertIn("cross-target contamination is forbidden", protocol)
        self.assertIn("Generalization into professional memory must preserve provenance", contract)

    def test_repair_preserves_identity_and_professional_state(self):
        installed = self.install(ready_overrides())
        before_identity = json.loads(installed[".context/service-agent/identity.json"])
        before_beliefs = installed[".context/service-agent/beliefs.md"]
        before_engagements = installed[".context/service-agent/engagements.md"]

        repaired = apply(installed, service_repair_changes(
            installed,
            SERVICE_TEMPLATES,
            repository="owner/service-agent",
            branch="main",
            core_commit="e" * 40,
        ))
        self.assertEqual(json.loads(repaired[".context/service-agent/identity.json"]), before_identity)
        self.assertEqual(repaired[".context/service-agent/beliefs.md"], before_beliefs)
        self.assertEqual(repaired[".context/service-agent/engagements.md"], before_engagements)
        self.assertEqual(json.loads(repaired[".context/capsule.json"])["core_commit"], "e" * 40)

    def test_runtime_checkpoint_is_not_service_agent_identity(self):
        installed = self.install(ready_overrides())
        installed[".context/runtime-checkpoint.json"] = '{"pending":"write-target"}'
        pack = build_service_recovery_pack(installed)
        self.assertNotIn("write-target", pack)

    def test_bounded_recovery_never_silently_drops_active_service_state(self):
        installed = self.install(ready_overrides())
        with self.assertRaisesRegex(
            ServiceAgentModelError,
            "recovery budget too small for mandatory service-agent state",
        ):
            build_service_recovery_pack(installed, max_chars=512)

    def test_profile_specific_state_can_be_mandatory_for_recovery(self):
        installed = self.install(ready_overrides())
        manifest = json.loads(installed[".context/manifest.json"])
        manifest["profile_state"]["mandatory"] = [
            ".context/profile/portfolio.md",
            ".context/profile/policies.md",
        ]
        manifest["profile_state"]["optional"] = [
            ".context/profile/history.md",
        ]
        installed[".context/profile/portfolio.md"] = "# Portfolio\n\nPROJECT_ALPHA_ACTIVE\n"
        installed[".context/profile/policies.md"] = "# Policies\n\nPROFILE_POLICY_MARKER\n"
        installed[".context/profile/history.md"] = "# History\n\nOPTIONAL_HISTORY_MARKER\n"
        installed[".context/manifest.json"] = json.dumps(manifest)

        self.assertEqual(validate_service_snapshot(installed), [])
        pack = build_service_recovery_pack(installed)
        self.assertIn("PROJECT_ALPHA_ACTIVE", pack)
        self.assertIn("PROFILE_POLICY_MARKER", pack)
        self.assertIn("OPTIONAL_HISTORY_MARKER", pack)

        repaired = apply(installed, service_repair_changes(
            installed,
            SERVICE_TEMPLATES,
            repository="owner/service-agent",
            branch="main",
            core_commit="f" * 40,
        ))
        repaired_manifest = json.loads(repaired[".context/manifest.json"])
        self.assertEqual(
            repaired_manifest["profile_state"],
            manifest["profile_state"],
        )

    def test_profile_version_is_explicit(self):
        installed = self.install(ready_overrides())
        meta = json.loads(installed[".context/capsule.json"])
        manifest = json.loads(installed[".context/manifest.json"])
        self.assertEqual(meta["profile_version"], SERVICE_AGENT_BASE_VERSION)
        self.assertEqual(manifest["profile_version"], SERVICE_AGENT_BASE_VERSION)
        self.assertEqual(
            (ROOT / "SERVICE_AGENT_BASE_VERSION").read_text(encoding="utf-8").strip(),
            SERVICE_AGENT_BASE_VERSION,
        )

    def test_identity_requires_role_and_specialization(self):
        installed = self.install(ready_overrides())
        identity = json.loads(installed[".context/service-agent/identity.json"])
        identity["role"] = ""
        installed[".context/service-agent/identity.json"] = json.dumps(identity)
        self.assertTrue(any(
            "role must be non-empty" in error
            for error in validate_service_snapshot(installed)
        ))


if __name__ == "__main__":
    unittest.main()
