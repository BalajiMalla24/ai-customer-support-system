# AI-Powered Customer Support System - Project Interview Brief

This document serves as your technical source of truth for interviews. It strips away the marketing fluff and focuses purely on architectural decisions, implementation details, and engineering trade-offs.

---

## 1. PROJECT OVERVIEW
**One-Sentence Pitch:** A multi-modal, agentic AI customer support system built with LangGraph that handles complex queries, contextual order tracking, and voice interactions while routing sensitive escalations to a secure local LLM.

**The Real-World Problem:** Traditional chatbots rely on rigid decision trees that fail on edge cases and frustrate users. Existing LLM wrappers hallucinate policies and leak sensitive PII during human handoffs. This project solves that by using a deterministic state machine (LangGraph) for workflow control, an adversarial "Critic" node to prevent hallucinations, and a hybrid cloud/local model routing strategy to protect privacy during escalations.

**Who Uses It:** 
- **End-Users (Customers):** Interact via a React-based web chat or voice interface to track orders, query return policies, and resolve issues.
- **Support Agents (Internal):** Receive rich, summarized "Escalation Bundles" when the AI cannot resolve an issue, ensuring they don't have to read through raw chat transcripts.

**Current Status:** Fully functional local development prototype. Deployed in a containerized Docker environment with mocked external OMS (Order Management System) endpoints.

---

## 2. FULL TECH STACK

**Frontend:**
- **Framework:** React 18, Vite
- **Styling:** Tailwind CSS (Vanilla CSS for base layer)
- **Key Components:** `ChatWindow.jsx` (handles WebSocket streaming and WebRTC MediaRecorder for voice), `AdminDashboard.jsx` (metrics and queue visualization).

**Backend:**
- **Framework:** FastAPI (Python 3.10+)
- **Concurrency:** Asyncio, WebSockets for real-time streaming, HTTPX for async external calls.

**Databases & Storage:**
- **Primary Database:** MongoDB (via Motor async driver) - Stores session history, aggregated dashboard metrics, and escalation queues (`backend/db/mongo.py`).
- **Caching & Sessions:** Redis (`redis.asyncio`) - Ephemeral session storage, active profile caching, and low-latency response caching (`backend/db/redis_store.py`, `backend/cache/response_cache.py`).
- **Vector Database:** FAISS (Facebook AI Similarity Search) - Local persistent index stored in `faiss_index_shopeasy/` for RAG (`backend/rag/faiss_store.py`).

**AI/ML Components:**
- **Orchestration:** LangGraph (StateGraph DAG).
- **Embeddings:** HuggingFace `all-MiniLM-L6-v2` (Local).
- **Model Routing Strategy (`backend/agents/llm_router.py`):**
  - **Primary Engine (Speed/Logic):** Groq `llama-3.3-70b-versatile` (Sub-second latency for standard routing and resolution).
  - **Critic Engine (Reasoning):** Google Gemini `gemini-1.5-flash` (Strong analytical capabilities for the QA loop).
  - **Escalation/Privacy Engine:** Local Ollama `llama3.2:3b` (Runs offline to generate PII-safe escalation summaries).
- **Voice Pipeline (`backend/voice_agent/pipeline.py`):**
  - **STT (Speech-to-Text):** OpenAI Whisper (Base model, local).
  - **VAD (Voice Activity Detection):** Custom implementation using Whisper segment probabilities.
  - **TTS (Text-to-Speech):** KittenTTS with automatic fallback to Edge-TTS.

---

## 3. CORE ARCHITECTURE & DATA FLOW

The system operates on a **LangGraph State Machine**. The central source of truth is the `AgentState` (`backend/agents/state.py`).

**Data Flow (Text Query):**
1. **Ingestion:** User sends text via WebSocket. `backend/main.py` intercepts, checks the Redis cache (`_make_scoped_cache_key`), and if it's a miss, invokes the LangGraph `app_graph`.
2. **Supervisor Node:** Analyzes intent (e.g., `track_order`, `policy`, `escalate`). It uses heuristics for speed but falls back to Groq for structured JSON parsing.
3. **Triage/Retrieval:** If intent is `policy`, it queries FAISS for RAG context. If `track_order`, it injects active order context from the mocked OMS (`in_memory_orders`).
4. **Resolution Node:** Groq generates a draft response based on the intent, conversation history, and retrieved context.
5. **Critic Node (The QA Loop):** Gemini evaluates the draft response against the retrieved context to detect hallucinations. It returns `APPROVE` or `REJECT`.
   - If `REJECT`: The graph loops back to Resolution with the Critic's feedback.
   - If `APPROVE`: The response is sent to the user and cached in Redis.
6. **Escalation:** If the user demands a human, or the retry limit (3) is hit in the Critic loop, the state moves to the Escalation node. Local Ollama generates a summary bundle, logs it to MongoDB, and notifies the user.

**Data Flow (Voice Query):**
1. User records audio via browser `MediaRecorder` in `ChatWindow.jsx`.
2. Audio blob (`.webm`) is sent via POST to `/api/voice/transcribe`.
3. `VoicePipeline.transcribe()` uses Whisper.
4. `VoicePipeline.run_vad()` and `detect_turn_end()` ensure the user has finished speaking.
5. Transcribed text follows the Text Query flow (or a low-latency fast-path `_fast_voice_reply` bypassing LangGraph if `VOICE_FAST_MODE` is enabled).
6. Response text is synthesized to audio via TTS and the URL is returned to the frontend.

---

## 4. AI/ML IMPLEMENTATION DETAILS

### LangGraph Agent Design
Unlike simple LangChain chains, I implemented a DAG (Directed Acyclic Graph) to allow cyclical reasoning. The `AgentState` object holds `messages`, `intent`, `retrieved_context`, `draft_response`, `critic_decision`, and `retry_count`. This prevents the LLM from losing context across nodes.

### RAG (Retrieval-Augmented Generation) Implementation
- **Splitting Strategy:** `RecursiveCharacterTextSplitter` chunking markdown documents (chunk size 500, overlap 50).
- **Index:** FAISS `IndexFlatL2`.
- **Querying:** When `retrieve_context` is called, the user query is embedded via `HuggingFaceEmbeddings`, and a similarity search returns the top 4 chunks.

### Dynamic Model Routing
I designed `get_llm()` in `llm_router.py` to decouple the task from a single provider:
- Hardcoding OpenAI is expensive and brittle.
- **Groq** is used for `task="routing"` because it outputs tokens at >300 t/s, crucial for the initial intent classification where user patience is low.
- **Ollama** is enforced for `task="escalation"`. I explicitly built this to demonstrate privacy-by-design. Handoff summaries often contain PII, so processing them locally ensures compliance.

---

## 5. ENGINEERING CHALLENGES & HOW I SOLVED THEM

**Challenge 1: Voice Mode Latency & "Turn Detection"**
*Problem:* Standard chatbots wait for the user to hit "Send". Voice interfaces need to know when the user is done talking. Naive silence detection cuts people off mid-sentence.
*Solution:* I built a custom VAD (Voice Activity Detection) in `backend/voice_agent/pipeline.py`. It uses Whisper's native `avg_no_speech_prob`. I combined acoustic silence thresholds with semantic end-of-utterance detection to create a natural conversational flow. I also implemented `_early_voice_reply_preview` in `main.py`—a zero-temperature, high-speed LLM call to return a provisional "thinking" string ("Let me check that order...") to mask TTS latency.

**Challenge 2: LLM Hallucinations on Edge Cases**
*Problem:* The LLM would confidently invent return policies if the RAG context was ambiguous.
*Solution:* I implemented the adversarial Critic Node (`critic_node`). By using a different model family (Gemini) to grade the primary model's (Groq) output, I reduced bias. The Critic enforces strict adherence to the FAISS context. If the draft response claims "returns are 30 days" but the RAG context says "15 days", Gemini rejects it, and the state graph forces a rewrite.

**Challenge 3: Rate Limits and Cost Management**
*Problem:* Calling Groq/Gemini on every single generic message ("Hi", "Thanks") wastes tokens and risks rate limiting.
*Solution:* I built an in-memory TTL cache (`ResponseCache` in `backend/cache/response_cache.py`) specifically scoped to the user's order context (`_make_scoped_cache_key`). Identical semantic queries with the same active order ID hit the cache in 0ms, bypassing LangGraph entirely.

---

## 6. MY SPECIFIC CONTRIBUTIONS

As the lead/sole engineer, I built the entire system end-to-end. Specific complex logic I authored:

1. **`backend/agents/nodes.py` & `backend/agents/graph.py`:** Wrote the core LangGraph state machine, including the conditional edge routing (`route_after_resolution`) that powers the QA loop.
2. **`backend/agents/llm_router.py`:** Implemented the environment-aware factory pattern for LLM initialization, ensuring fallback mechanisms.
3. **`backend/voice_agent/pipeline.py`:** Engineered the `VoicePipeline` class, integrating Whisper, custom VAD, and asynchronous TTS synthesis.
4. **`backend/main.py`:** Built the FastAPI WebSocket manager (`ConnectionManager`), the memory/MongoDB fallback logic, and the contextual order injection (`_resolve_order_context`).
5. **`backend/db/redis_store.py`:** Implemented a resilient Redis wrapper (`RedisSessionManager`) that degrades gracefully to in-memory dicts if the Redis container crashes, ensuring high availability.

---

## 7. INTERVIEW CHEAT SHEET (Q&A FORMAT)

**Q: Why LangGraph instead of standard LangChain Agents?**
**A:** "Standard LangChain agents use the ReAct pattern, which relies on the LLM to decide its next step. That's non-deterministic and prone to infinite loops. LangGraph allows me to define a strict, cyclical DAG. I needed a deterministic workflow—Supervisor -> Retrieval -> Resolution -> Critic—where I control the edges, but the LLM controls the data."

**Q: How are you handling context windows and memory?**
**A:** "I use a dual-layer approach. Redis handles short-term ephemeral session memory for fast retrieval during the active chat. MongoDB persists the long-term history. Before invoking the graph, I load the last N messages from Redis to construct the `HumanMessage` and `AIMessage` history array."

**Q: Tell me about a time you had to optimize performance.**
**A:** "Voice latency was a major issue. Whisper transcription + Groq generation + TTS synthesis took >3 seconds. I optimized this by: 1) Caching responses using a semantic key based on user text and active order ID. 2) Implementing a `VOICE_FAST_MODE` that bypasses LangGraph entirely for simple queries, doing a direct RAG + Groq call. 3) Keeping Whisper loaded in memory globally on app startup rather than initializing it per request."

**Q: What would you change to make this production-ready?**
**A:** "Three things: 
1. **Security:** Implement JWT authorization on the `/api/admin` routes and WebSocket connections.
2. **Integration:** Replace the `in_memory_orders` mock in `main.py` with an actual HTTPX client hitting the real OMS API, adding circuit breakers.
3. **Storage:** Move the FAISS index to a managed vector DB like Pinecone or Qdrant for horizontal scalability, and implement a cron job (Celery) to purge stale `.wav` files in `backend/voice_output/` to prevent disk bloat."

**Q: Why did you use local Ollama for escalation?**
**A:** "Privacy by design. When a user is angry and demands a human, the escalation bundle includes their full chat history, which often leaks PII (names, emails, partial addresses). By routing the summarization task to a local Llama 3.2 3B model via Ollama, I guarantee that sensitive context never leaves the VPC before being handed to an internal support agent."
