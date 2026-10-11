#!/usr/bin/env python
"""
Phase 3: Escalation Agent
Context bundle generator for human handoff (uses Ollama local)
"""

import json
import os

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


async def generate_escalation_bundle(
    conversation_history: list[str],
    user_query: str, 
    intent: str,
    priority: str,
    retrieved_context: str,
    critic_feedback: str = ""
) -> dict:
    """
    Generate a context bundle for human agent handoff.
    
    Uses Ollama locally to summarize conversation + sentiment + recommendations.
    This runs synchronously on CPU; no external API calls.
    """
    print("[ESCALATION] Generating context bundle for human handoff...")
    
    llm = ChatOllama(model=OLLAMA_MODEL, temperature=0.0)
    
    conversation_text = "\n".join(conversation_history[-10:])  # Last 10 turns
    
    sys_prompt = f"""You are a human support agent briefing generator. Create a concise JSON summary.

CONVERSATION (last turns):
{conversation_text}

USER QUERY: {user_query}
INTENT CLASSIFIED: {intent}
PRIORITY: {priority}
CONTEXT: {retrieved_context}
CRITIC FEEDBACK: {critic_feedback}

Generate JSON with NO extra text:
{{
  "summary": "1-2 sentence concise summary of issue",
  "sentiment": "positive|neutral|negative|angry",
  "suggested_resolution": "concrete next step for agent",
  "key_facts": ["fact1", "fact2"],
  "escalation_reason": "why bot could not resolve"
}}
"""
    
    response = llm.invoke([SystemMessage(content=sys_prompt)])
    
    try:
        # Extract JSON from response
        text = response.content.strip()
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_text = text[start:end+1]
            bundle = json.loads(json_text)
        else:
            bundle = {
                "summary": text[:200],
                "sentiment": "neutral",
                "suggested_resolution": "Escalate to human support",
                "key_facts": [],
                "escalation_reason": "Automated resolution failed"
            }
    except Exception as e:
        print(f"[ESCALATION] JSON parse error: {e}")
        bundle = {
            "summary": f"Customer issue: {user_query[:100]}",
            "sentiment": "neutral",
            "suggested_resolution": "Escalate to human support",
            "key_facts": [],
            "escalation_reason": str(e)
        }
    
    return {
        "session_created": True,
        "context_bundle": bundle,
        "ready_for_handoff": True,
        "queue_message": "Customer escalated to human support queue"
    }


if __name__ == "__main__":
    # Test escalation bundle generation
    import asyncio
    
    test_history = [
        "user: Where is my order?",
        "bot: I can help you track your order. What's your order ID?",
        "user: SE-4821",
        "bot: Your order SE-4821 (Bluetooth Speaker) is in transit. Estimated delivery is tomorrow.",
        "user: That's not acceptable. I need it today!",
    ]
    
    test_bundle = asyncio.run(generate_escalation_bundle(
        conversation_history=test_history,
        user_query="I need my order today",
        intent="complaint",
        priority="P2",
        retrieved_context="Standard shipping: 2-5 days. Express shipping: next day.",
        critic_feedback="Draft did not address urgency properly."
    ))
    
    print("\n[ESCALATION BUNDLE]")
    print(json.dumps(test_bundle, indent=2))
