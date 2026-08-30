from langgraph.graph import END, START, StateGraph

from .agents import ClinicalState, knowledge_node, referral_node, safety_node, scribe_node, triage_node


def _route_after_safety(state: ClinicalState) -> str:
    if state.get("blocked"):
        return "blocked"
    if state.get("emergency"):
        return "emergency"
    return "triage"


_builder = StateGraph(ClinicalState)
_builder.add_node("safety", safety_node)
_builder.add_node("triage", triage_node)
_builder.add_node("knowledge", knowledge_node)
_builder.add_node("referral", referral_node)
_builder.add_node("scribe", scribe_node)
_builder.add_edge(START, "safety")
_builder.add_conditional_edges(
    "safety",
    _route_after_safety,
    {"blocked": END, "emergency": "referral", "triage": "triage"},
)
_builder.add_edge("triage", "knowledge")
_builder.add_edge("knowledge", "referral")
_builder.add_edge("referral", "scribe")
_builder.add_edge("scribe", END)
clinical_graph = _builder.compile()


def run_clinical_workflow(payload: ClinicalState) -> ClinicalState:
    return clinical_graph.invoke(payload)
