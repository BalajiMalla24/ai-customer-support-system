# AI-Powered Customer Support System
### Product Requirements Document
**Version 1.0 | March 2026 | Woxsen University | B.Tech CSE (Data Science) | 8th Semester Industry Track**

---

| 6 Specialized Agents | 3 LLM Providers | 5 Core Channels | 100% Req. Coverage |
|---|---|---|---|

---

## 1. Project Overview

### 1.1 Vision Statement

The AI-Powered Customer Support System is a production-grade, multi-agent platform that handles support requests across chat, email, voice, and ticket channels without human intervention for tier-1 and tier-2 issues. It uses a hybrid LLM architecture — cloud models for complex reasoning, local models for sensitive/offline tasks — backed by a RAG knowledge engine, and hands off to humans only for critical escalations.

### 1.2 Why This Project Stands Out

This project satisfies every requirement in the Agentic AI brief and goes further with differentiating features:

> **Requirement Coverage vs. Project Features**
> - **Agent Orchestration** → LangGraph stateful multi-agent DAG with 6 specialized agents
> - **Planning & Reasoning** → Triage Agent decomposes every ticket into intent + sub-tasks + priority
> - **Memory Integration** → Short-term (session) + long-term (MongoDB) + episodic (customer history)
> - **RAG** → FAISS semantic search over KB + Elasticsearch keyword fallback + metadata filtering
> - **Offline/Local Model** → Ollama (llama3.2) runs locally for escalation drafts & data-sensitive tasks
> - **Tool Usage** → 8+ integrated tools: order APIs, CRM, email, sentiment analyzer, ticket system, calendar

### 1.3 Unique Differentiators

- **Voice Agent with STT + TTS (Whisper + KittenTTS)** — real-time spoken support, not just text
- **Hybrid LLM Router** — dynamically chooses Groq/llama-3.3-70b, Gemini 1.5 Flash, or Ollama based on task type, latency budget, and data sensitivity
- **Adversarial Reasoning** — a Critic Agent independently checks every response before it is sent, reducing hallucination risk
- **Auto-Escalation with Context Bundle** — when escalating to human, agent packages full conversation summary + sentiment timeline + suggested resolution
- **Agent Memory Timeline** — every customer interaction stored with vector embeddings; agents recall past issues without re-reading history

---

## 2. System Architecture

### 2.1 High-Level Architecture Narrative

The system is a layered architecture with five logical tiers:

1. **Ingestion Layer** — Multi-channel adapters (WebSocket for chat, SMTP/IMAP for email, REST webhook for tickets, WebRTC for voice) normalize incoming messages into a unified event schema before they enter the pipeline.

2. **Orchestration Layer** — LangGraph manages the agent DAG. Each node is a specialized agent; edges are conditional transitions based on intent, confidence, and task state. The Supervisor Agent is the entry point and router.

3. **Intelligence Layer** — Each agent calls the LLM Router which selects the appropriate model. RAG retrieval happens here via FAISS + Elasticsearch. Tools (APIs, DBs) are called as needed.

4. **Memory Layer** — Three memory types: Redis for session state (TTL 30 min), MongoDB for persistent customer history, FAISS for semantic recall of past resolutions.

5. **Delivery Layer** — Responses are formatted per channel (HTML email, markdown chat, SSML voice), quality-checked by the Critic Agent, then dispatched. Human handoff triggers a live-agent notification with context bundle.

### 2.2 Agent Roster

| Agent | Role | Model Used |
|---|---|---|
| **Supervisor Agent** | Entry point. Classifies intent, routes to correct specialist, maintains conversation state | Groq / llama-3.3-70b |
| **Triage Agent** | Decomposes query into sub-tasks, assigns priority (P1–P4), estimates resolution path | Groq / llama-3.3-70b |
| **Resolution Agent** | Handles tier-1 and tier-2 issues: order tracking, refunds, FAQs, tech troubleshooting using RAG + tools | Groq / llama-3.3-70b |
| **Escalation Agent** | Decides when human handoff is needed; prepares context bundle; notifies live agent queue | Ollama (llama3.2 — local) |
| **Critic Agent** | Reviews every drafted response for accuracy, tone, and hallucination before dispatch | Gemini 1.5 Flash |
| **Voice Agent** | STT via Whisper → text pipeline → TTS via KittenTTS; manages real-time voice session lifecycle | Whisper + KittenTTS + Groq |

### 2.3 LangGraph Flow

```
START
  └─► Supervisor Agent
        ├─► Triage Agent (complex/new query)
        │     └─► Resolution Agent
        └─► Resolution Agent (simple FAQ)
               ├─► Critic Agent
               │     ├─► APPROVED ──► Delivery (response sent)
               │     ├─► REJECTED ──► Resolution Agent (retry, max 2x)
               │     └─► ESCALATE ──► Escalation Agent
               └─► Escalation Agent (confidence < 0.6 or P1)
                     └─► END (human queue notified)

Voice Agent = parallel wrapper around entire graph
  Audio ──► Whisper STT ──► Supervisor ──► ... ──► KittenTTS ──► Audio response
```

---

## 3. Tech Stack & Frameworks

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 19 + Vite | Chat UI, Admin Dashboard, Voice interface |
| Frontend | Tailwind CSS | Styling, responsive layout |
| Frontend | Socket.IO (client) | Real-time WebSocket messages |
| Frontend | Web Audio API | Voice recording + KittenTTS playback |
| Backend | FastAPI (Python) | REST API, WebSocket endpoints, orchestration entry |
| Backend | LangGraph 0.2+ | Multi-agent DAG orchestration |
| Backend | LangChain | Tool wrappers, prompt templates, chain utilities |
| LLM (Cloud) | Groq API / llama-3.3-70b | Primary agent reasoning — ultra-low latency |
| LLM (Cloud) | Google Gemini 1.5 Flash | Critic Agent — fast, accurate review |
| LLM (Local) | Ollama + llama3.2:3b Q4_K_M | Escalation Agent — offline, no data leaves system |
| STT | OpenAI Whisper base (74MB, CPU/CUDA) | Speech-to-text for Voice Agent |
| TTS | KittenTTS nano-int8 (25MB, ONNX, CPU) | Text-to-speech — local, free, 8 voices |
| Vector DB | FAISS | Semantic KB search + memory recall |
| Search | Elasticsearch | Keyword fallback for exact-match queries |
| Session State | Redis | Short-term agent memory, session TTL |
| Persistent DB | MongoDB Atlas | Customer history, ticket logs, escalation records |
| Auth | JWT + FastAPI Security | Agent dashboard, admin panel access |
| Queue | Celery + Redis broker | Async email processing, background ticket ingestion |
| Email | SMTP/IMAP + Python email | Email channel ingestion and dispatch |
| Containerization | Docker + Docker Compose | Reproducible local dev + deployment |

---

## 4. Feature Specifications

### F1 — Multi-Channel Ingestion

| Attribute | Detail |
|---|---|
| Channels | Live Chat (WebSocket), Email (SMTP/IMAP), Support Ticket (REST), Voice (file upload / mic) |
| Unified Schema | Every message normalizes to: `channel`, `customer_id`, `message_text`, `timestamp`, `metadata` |
| Rate Limiting | FastAPI middleware throttles per IP to prevent abuse |

### F2 — Intent Classification & Triage

| Attribute | Detail |
|---|---|
| Intent Types | Order Tracking, Refund Request, Technical Issue, General FAQ, Complaint, Escalation Request |
| Priority Levels | P1 (critical/outage), P2 (billing/refund), P3 (tech support), P4 (general inquiry) |
| Sub-task Decomposition | Triage Agent uses CoT prompting to break complex requests into sequential resolution steps |
| Confidence Scoring | Each classification includes a 0–1 confidence score; below 0.6 triggers clarification request |

### F3 — RAG Knowledge Base

| Attribute | Detail |
|---|---|
| Document Types | Product manuals, FAQ docs, policy PDFs, past resolution logs |
| Chunking Strategy | Semantic chunking — 512 token chunks with 64 token overlap |
| Retrieval | FAISS cosine similarity top-5 + Elasticsearch keyword top-3; results re-ranked by MMR |
| Metadata Filtering | Filter by category (shipping, billing, tech) before retrieval to reduce noise |
| KB Update | Admin uploads new docs; background Celery job re-indexes automatically |
| Persistence | FAISS index saved to `faiss_index.bin`; loaded on startup |

### F4 — Voice Agent

| Attribute | Detail |
|---|---|
| STT | Whisper base (74MB, local). Downloads once to `~/.cache/whisper/`. CUDA-accelerated if GPU available. |
| TTS | KittenTTS nano-int8 (25MB, ONNX, CPU). RTF < 0.8 on i7/Ryzen 7. Sub-second per sentence. |
| Pipeline | Audio → Whisper → text → Supervisor Agent → response → KittenTTS → audio |
| Voice Selection | Default: `Jasper` (male, neutral). 8 voices available. Admin-configurable. |
| Voice Session State | Stored in Redis with same session schema as text channels |

### F5 — Critic Agent QA Loop

| Attribute | Detail |
|---|---|
| Check Dimensions | Factual accuracy (vs retrieved KB), tone (empathetic/professional), hallucination detection, completeness |
| Decision | `APPROVE` (send), `REJECT+FEEDBACK` (retry), `ESCALATE` (too uncertain) |
| Max Retries | 2 regeneration attempts before forced escalation |
| Audit Log | Every Critic decision logged with reason for post-analysis |

### F6 — Human Escalation with Context Bundle

| Attribute | Detail |
|---|---|
| Trigger Conditions | P1 ticket, Critic rejects 2x, customer explicitly requests human, sentiment score < -0.4 |
| Context Bundle | Conversation summary (Ollama-generated, local), sentiment timeline, category, suggested resolution, customer history snippet |
| Delivery | Bundle sent to live-agent queue via WebSocket + MongoDB record |
| Customer Message | Auto-sends acknowledgment with estimated wait time |

---

## 5. UI / Frontend Design

### 5.1 Customer-Facing Chat Interface

- **Chat Window** — message thread with agent avatar indicator. Timestamps, read receipts, typing indicator while agent processes.
- **Voice Button** — floating mic button. Shows audio waveform during recording. KittenTTS audio response auto-plays.
- **Ticket Status Card** — shows live status: `Triaging → Resolving → Resolved / Escalated` with progress bar.

### 5.2 Admin Dashboard

- **Live Queue Panel** — real-time view of all active sessions. Color-coded by priority (P1 red, P2 orange, P3 yellow, P4 green). One-click to join escalated sessions.
- **Analytics Panel** — avg resolution time per category, escalation rate, Critic reject rate, agent utilization. MongoDB-aggregated.
- **KB Management Panel** — upload documents, view indexed chunks, trigger re-indexing, set category tags.

### 5.3 Component Map

| Component | Location | Tech |
|---|---|---|
| `ChatWindow` | Customer portal | React + Socket.IO |
| `VoiceRecorder` | Customer portal | Web Audio API + Axios |
| `TicketStatusTracker` | Customer portal | React + polling / SSE |
| `LiveQueuePanel` | Admin dashboard | React + Socket.IO |
| `SentimentBadge` | Admin dashboard (per ticket) | Tailwind color chips |
| `AnalyticsCharts` | Admin dashboard | Recharts + MongoDB aggregation |
| `KBUploader` | Admin dashboard | React dropzone + FastAPI multipart |
| `EscalationContextCard` | Live agent view | React modal with timeline |

---

## 6. Backend Logic Design

### 6.1 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat/message` | POST | Receive text message, return `session_id` + queued status |
| `/ws/chat/{session_id}` | WS | WebSocket stream for real-time chat responses |
| `/api/voice/upload` | POST | Multipart audio → Whisper STT → pipeline → KittenTTS audio response |
| `/api/ticket/create` | POST | Create support ticket from any channel |
| `/api/ticket/{id}/status` | GET | Live ticket status and resolution summary |
| `/api/admin/queue` | GET | All active sessions for live-agent panel |
| `/api/admin/kb/upload` | POST | Upload and index new KB document |
| `/api/admin/analytics` | GET | Pre-aggregated analytics for dashboard |
| `/api/escalate/{session_id}` | POST | Manually trigger escalation with context bundle |

### 6.2 Agent Prompting Strategy

- **Supervisor** — outputs structured JSON: `{intent, confidence, priority, next_agent}`. 6 intent categories with few-shot examples. Strict JSON output enforced.
- **Triage** — CoT prompt: *"First identify the root cause, then list each sub-task required, then assign a priority based on business impact."* Output: `{subtasks[], priority, estimated_steps}`.
- **Resolution** — injected with `[RAG context chunks]` + `[tool results]` + `[customer history snippet]`. Forbidden from fabricating order IDs or policy clauses. Must cite KB source used.
- **Critic** — receives `{draft_response, retrieved_context, original_query}`. Must output: `{decision: APPROVE/REJECT/ESCALATE, confidence, reason}`. Short and decisive.
- **Escalation (Ollama, local)** — *"Write a neutral, factual 200-word context bundle for the live agent. Include conversation summary, sentiment trend, category, and suggested resolution. No customer-facing language."*

### 6.3 Memory Architecture

| Type | Store | Detail |
|---|---|---|
| Session Memory | Redis | Last 20 turns per session. Key: `session_id`. TTL: 30 min inactivity. |
| Customer History | MongoDB Atlas | All past tickets, resolutions, CSAT. Queried at session start for repeat customers. |
| Semantic Memory | FAISS | Past successful resolutions embedded. Top-3 similar cases injected into Resolution Agent prompt. |

---

## 7. Constraints & Mitigation Strategies

| Constraint | Risk | Mitigation Strategy |
|---|---|---|
| Groq API rate limits (30 req/min free tier) | Agents bottleneck under concurrent load | Celery request queue + exponential backoff + fallback to Gemini Flash if Groq throttled |
| Ollama on CPU-only (no GPU offload for 7B+) | Slow inference on CPU | Use `llama3.2:3b Q4_K_M` (~2.5GB RAM). On GTX 1650 4GB: ~18-20 tok/s GPU-accelerated. On CPU-only: 8-12 tok/s — acceptable for escalation drafts only. |
| Whisper transcription latency | Voice responses feel slow | Use `whisper base` (74MB). On CUDA (GTX 1650): under 1s for 10s clip. On CPU: 2-4s. Cap voice input at 15s. |
| KittenTTS developer preview | API may change; artifacts on unusual input | Pin to v0.8.1 wheel. Test all demo phrases in advance. Keep gTTS as fallback in same code path. |
| FAISS not persistent across restarts | KB lost on every server restart | Save index to `faiss_index.bin` on disk. Load on startup. Re-index only on new document upload. |
| No real CRM/order API | Order tracking non-functional | Mock FastAPI router returns realistic fixture data. Labeled "Simulated" in demo. |
| LLM hallucination in responses | Fabricated policy details or order info | Critic Agent mandatory QA pass + Resolution Agent forbidden-clause prompt rules + RAG grounding |
| WebSocket connection management | Memory/connection leak under multiple sessions | Redis pub/sub for session state. FastAPI lifespan handlers clean up on disconnect. |
| 3-day build timeline | Not all features fully polished | Prioritize: Chat + RAG + Triage + Critic (core). Voice and Email are Day 3 additions. Admin dashboard ships with stub data if needed. |

---

## 8. 3-Day Build Plan

| Day | Focus | Deliverable |
|---|---|---|
| **Day 1** | Core Pipeline | FastAPI setup, LangGraph DAG (Supervisor + Triage + Resolution), FAISS RAG with sample KB, basic React chat UI, WebSocket working end-to-end |
| **Day 2** | Quality & Memory | Critic Agent, MongoDB customer history, Redis session memory, Ollama Escalation Agent, Admin queue panel, Sentiment scoring |
| **Day 3** | Voice + Polish | Voice Agent (Whisper + KittenTTS), email channel, Analytics panel, full demo script, README, slide deck |

---

## 9. Demo Script (Presentation Day)

Five scenarios to cover in 5 minutes:

1. **Order Tracking (text)** — Customer types *"Where is my order #12345?"* → Supervisor classifies → Resolution Agent queries mock order API → Critic approves → response in <2s.

2. **Complex Refund (text)** — Customer sends angry message about billing error → Triage assigns P2 → Resolution retrieves refund policy from RAG → Critic rejects first draft (tone issue) → retry → Critic approves → sent.

3. **Escalation Flow** — P1 issue (service outage report) → Escalation Agent generates context bundle → Admin queue panel shows notification in real-time.

4. **Voice Query** — Mic input → Whisper transcription shown on screen → same agent pipeline → KittenTTS audio response plays back.

5. **Admin Dashboard** — Live queue, analytics charts (resolution time, escalation rate), KB upload triggering re-index.

---

## 10. Success Criteria

- [ ] All 6 agentic requirements from the brief are demonstrably satisfied in the live demo
- [ ] End-to-end response time for tier-1 queries under 3 seconds (Groq inference)
- [ ] Critic Agent catches at least one hallucination or tone issue during the demo flow
- [ ] Voice channel works end-to-end in the presentation environment
- [ ] Escalation with context bundle visible in admin panel in real-time
- [ ] Entire system runs with zero paid API costs
- [ ] Single `docker-compose up` starts entire backend stack

---

*AI Customer Support System | PRD Version 1.0 | Woxsen University 2026*
