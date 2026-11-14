"""Small deterministic clinical graph.

Preserves the same LangGraph node order and emergency/blocked branches without
bundling the entire LangChain/LangGraph runtime into every Vercel Function.
Safety decisions always run first; model output must never override them.
"""
from __future__ import annotations

from .agents import ClinicalState, knowledge_node, referral_node, safety_node, scribe_node, triage_node


def run_clinical_workflow(payload: ClinicalState) -> ClinicalState:
    state: ClinicalState = dict(payload)
    state.update(safety_node(state))
    if state.get("blocked"):
        return state
    if not state.get("emergency"):
        state.update(triage_node(state))
        state.update(knowledge_node(state))
    state.update(referral_node(state))
    state.update(scribe_node(state))
    return state
