from langgraph.graph import END, START, StateGraph

from .nodes import critic_node, resolution_node, supervisor_node, triage_node
from .state import AgentState


def build_graph():
    workflow = StateGraph(AgentState)
    
    # 1. Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("triage", triage_node)
    workflow.add_node("resolution", resolution_node)
    workflow.add_node("critic", critic_node)
    
    # 2. Add edges
    workflow.add_edge(START, "supervisor")
    
    def route_from_supervisor(state: AgentState):
        if state.get("escalate", False):
            return END  # Or route to manual escalation agent
        if state.get("classification_confidence", 1.0) < 0.6:
            return "triage"
        if state.get("is_complex", False):
            return "triage"
        if state.get("intent") in ["complaint", "technical", "refund"]:
            return "triage"
        return "resolution"
        
    workflow.add_conditional_edges("supervisor", route_from_supervisor)
    workflow.add_edge("triage", "resolution")

    def route_from_resolution(state: AgentState):
        if state.get("resolved_by_rules", False):
            return END
        # Fast-path: skip critic for trivial greeting responses.
        if state.get("intent") == "general" and state.get("retrieved_context", "") == "":
            return END
        return "critic"

    workflow.add_conditional_edges("resolution", route_from_resolution)
    
    def route_from_critic(state: AgentState):
        decision = str(state.get("critic_decision", "ESCALATE")).upper()
        if decision == "APPROVE":
            return END
        elif decision == "REJECT":
            if state.get("retry_count", 0) >= 2:
                return END
            return "resolution"
        else:
            return END
            
    workflow.add_conditional_edges("critic", route_from_critic)
    
    # Compile
    app_graph = workflow.compile()
    return app_graph

app_graph = build_graph()
