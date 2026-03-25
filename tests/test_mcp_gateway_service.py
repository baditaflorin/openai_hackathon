from __future__ import annotations

import unittest

from clipmato.services.mcp_gateway import DRY_RUN_MODE, LIVE_APPLY_MODE, MCPGatewayService


class MCPGatewayServiceTests(unittest.TestCase):
    def test_capability_negotiation_filters_features_and_scopes(self) -> None:
        gateway = MCPGatewayService()

        negotiated = gateway.negotiate_capabilities(
            client_schema_version="1.2",
            client_features=["dry_run", "unknown"],
            client_scopes=["runtime", "publish", "missing"],
        )

        self.assertTrue(negotiated.compatible)
        self.assertEqual(negotiated.negotiated_schema_version, "1.0")
        self.assertEqual(negotiated.accepted_client_features, ("dry_run",))
        self.assertEqual(negotiated.accepted_scopes, ("publish", "runtime"))
        self.assertEqual({tool.name for tool in negotiated.tools}, {"runtime.settings.read", "runtime.settings.update", "runtime.profile.apply", "publish.record"})

    def test_dry_run_invocation_does_not_apply_changes(self) -> None:
        seen: list[tuple[str, str]] = []

        def executor(invocation, definition):
            seen.append((invocation.tool_name, invocation.mode))
            return {"preview": True, "updates": invocation.arguments.get("updates", {})}

        gateway = MCPGatewayService(tool_executor=executor)

        result = gateway.invoke_tool(
            "runtime.settings.update",
            {"updates": {"content_backend": "ollama"}},
            run_id="run-1",
            mode=DRY_RUN_MODE,
            scopes=["runtime"],
        )

        self.assertTrue(result.ok)
        self.assertFalse(result.applied)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.output["updates"], {"content_backend": "ollama"})
        self.assertEqual(seen, [("runtime.settings.update", "dry_run")])
        self.assertEqual(gateway.get_run_state("run-1").state, "completed")

    def test_live_apply_invocation_uses_executor(self) -> None:
        def executor(invocation, definition):
            return {"applied": True, "profile": invocation.arguments["profile"]}

        gateway = MCPGatewayService(tool_executor=executor)

        result = gateway.invoke_tool(
            "runtime.profile.apply",
            {"profile": "local-offline"},
            run_id="run-2",
            mode=LIVE_APPLY_MODE,
            scopes=["runtime"],
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.applied)
        self.assertEqual(result.output["profile"], "local-offline")
        self.assertEqual(gateway.get_run_state("run-2").final_outcome, "success")

    def test_sensitive_tool_requires_approval(self) -> None:
        gateway = MCPGatewayService(tool_executor=lambda *_args: {"applied": True})

        result = gateway.invoke_tool(
            "credentials.update",
            {"updates": {"openai_api_key": "sk-test"}},
            run_id="run-3",
            mode=LIVE_APPLY_MODE,
            scopes=["credentials"],
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "approval_required")
        self.assertEqual(gateway.get_run_state("run-3").state, "awaiting_approval")

    def test_unknown_tool_returns_machine_readable_error(self) -> None:
        gateway = MCPGatewayService()

        result = gateway.invoke_tool("missing.tool", {}, mode=LIVE_APPLY_MODE)

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "unknown_tool")
        self.assertEqual(result.error.details["tool_name"], "missing.tool")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
