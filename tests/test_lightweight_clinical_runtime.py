"""Minimal-runtime regression tests. No real patient data or provider calls."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.clinical import graph
from app.clinical import gemini_rest
from app.clinical.guardrails import evaluate_input


class WorkflowTests(unittest.TestCase):
    def test_emergency_bypasses_model_triage_and_knowledge(self):
        state = {"message": "I have crushing chest pain and cannot breathe"}
        with (
            patch.object(graph, "triage_node") as triage,
            patch.object(graph, "knowledge_node") as knowledge,
            patch.object(graph, "referral_node", return_value={"referrals": []}) as referral,
            patch.object(graph, "scribe_node", return_value={"soap_note": {"plan": ["Urgent clinical review"]}}) as scribe,
        ):
            output = graph.run_clinical_workflow(state)
        self.assertTrue(output["emergency"])
        self.assertEqual(output["urgency"], "emergency")
        triage.assert_not_called()
        knowledge.assert_not_called()
        referral.assert_called_once()
        scribe.assert_called_once()
        self.assertEqual(output["message"], state["message"])

    def test_blocked_request_stops_before_all_followup_nodes(self):
        with (
            patch.object(graph, "triage_node") as triage,
            patch.object(graph, "knowledge_node") as knowledge,
            patch.object(graph, "referral_node") as referral,
            patch.object(graph, "scribe_node") as scribe,
        ):
            output = graph.run_clinical_workflow({"message": "write my essay"})
        self.assertTrue(output["blocked"])
        for node in (triage, knowledge, referral, scribe):
            node.assert_not_called()

    def test_routine_preserves_full_order_and_merged_state(self):
        trace = []
        def part(name, result):
            def apply(state):
                trace.append(name)
                return result
            return apply
        with (
            patch.object(graph, "safety_node", side_effect=part("safety", {"blocked": False, "emergency": False})),
            patch.object(graph, "triage_node", side_effect=part("triage", {"structured_intake": {}})),
            patch.object(graph, "knowledge_node", side_effect=part("knowledge", {"evidence": []})),
            patch.object(graph, "referral_node", side_effect=part("referral", {"referrals": []})),
            patch.object(graph, "scribe_node", side_effect=part("scribe", {"soap_note": {}})),
        ):
            out = graph.run_clinical_workflow({"message": "headache"})
        self.assertEqual(trace, ["safety", "triage", "knowledge", "referral", "scribe"])
        self.assertEqual(out["message"], "headache")
        self.assertIn("soap_note", out)

    def test_red_flags_are_still_deterministic(self):
        self.assertTrue(evaluate_input("I have crushing chest pain").emergency)


class GeminiRestTests(unittest.TestCase):
    def test_credentials_never_appear_in_url_and_endpoint_cannot_be_overridden(self):
        reply = Mock()
        reply.status_code = 200
        reply.content = b'{"candidates":[{"content":{"parts":[{"text":"{}"}]}}]}'
        reply.json.return_value = json.loads(reply.content)
        client = Mock()
        client.post.return_value = reply
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        with (
            patch.object(gemini_rest.settings, "GEMINI_API_KEY", "dummy-test-key"),
            patch.object(gemini_rest.settings, "GOOGLE_API_KEY", ""),
            patch.object(gemini_rest.httpx, "Client", return_value=client),
        ):
            result = gemini_rest.generate_json_text("Only JSON", "synthetic test")
        self.assertEqual(result, "{}")
        self.assertEqual(client.post.call_args.kwargs["headers"]["x-goog-api-key"], "dummy-test-key")
        self.assertNotIn("dummy-test-key", client.post.call_args.args[0])
        self.assertTrue(client.post.call_args.args[0].startswith("https://generativelanguage.googleapis.com/"))

    def test_bad_model_identifier_fails_closed(self):
        self.assertIsNone(gemini_rest._model("../bad/model"))
        self.assertIsNone(gemini_rest._model("http://elsewhere.test"))

    def test_embeddings_invalid_payload_fails_closed(self):
        with (
            patch.object(gemini_rest.settings, "GEMINI_API_KEY", "dummy-test-key"),
            patch.object(gemini_rest.settings, "GOOGLE_API_KEY", ""),
            patch.object(gemini_rest, "_call", return_value={"embedding": {"values": [0.1, float("nan")]}}),
        ):
            self.assertIsNone(gemini_rest.embed_query("synthetic clinical document"))


if __name__ == "__main__":
    unittest.main()
