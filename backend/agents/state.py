from typing import Annotated, List, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State payload managed by LangGraph across all agents
    """
    session_id: str
    messages: Annotated[list, add_messages]
    
    # Track intents and priority
    intent: str
    classification_confidence: float
    is_complex: bool
    priority: str
    subtasks: List[str]
    estimated_steps: int
    triage_confidence: float
    
    # Retrieval and Generations
    retrieved_context: str
    draft_response: str
    
    # Critic validations
    critic_decision: str
    critic_feedback: str
    
    # Control flags
    escalate: bool
    retry_count: int
    resolved_by_rules: bool
