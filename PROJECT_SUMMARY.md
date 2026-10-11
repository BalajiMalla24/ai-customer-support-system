# PROJECT SUMMARY

Generated on: 2026-03-26
Workspace root: `d:/Industry Track Project`

## 1. Project Status Overview

### Complete

- Backend infrastructure (`FastAPI`, startup/shutdown lifecycle, CORS).
- LangGraph DAG and state flow (`Supervisor -> Triage -> Resolution -> Critic`, escalation exits).
- Agent node implementations (Supervisor, Triage, Resolution, Critic).
- Escalation bundle generation (`Ollama` local summarization path).
- Multi-model LLM router (`Groq`/`Gemini`/`Ollama`) with task-specific routing.
- Voice mode pipeline (`Whisper STT`, VAD + semantic turn detection, TTS synthesis).
- Streaming voice WebSocket with auto-silence turn finalization.
- Streaming partial transcript + early reply preview for perceived latency reduction.
- Chat UI + WebSocket flow.
- Admin dashboard metrics/queue/analytics + KB upload.
- MongoDB persistence layer (sessions/history/analytics aggregations).
- Redis session layer (history/meta/profile/email queue) with in-memory fallback for profiles.
- Email inbound channel with optional SMTP outbound.
- RAG using FAISS + embeddings, KB append/reindex support.
- Mock order tooling (single order, order list, session-scoped order summary, order events timeline).

### Partially Done

- Tool integrations are functional but still mock/simulated for production use.
  - Order data is local/mock + Mongo-backed, not a real commerce backend integration.
  - Email outbound depends on SMTP credentials currently not set in env.
- Production hardening (auth, observability, tests, deployment quality gates) is incomplete.

### Not Started / Missing for Production Grade

- Automated test suite (unit/integration/e2e) is not present.
- CI/CD pipeline and release workflows are not configured.
- Role-based auth/authorization for admin APIs is not implemented.
- Real external systems integration (CRM/order management/helpdesk) is not implemented.

## 2. Current Folder Structure

Note: This tree includes all meaningful project files in the app workspace and excludes dependency/build caches (`venv`, `node_modules`, `dist`, `__pycache__`) to keep the report usable.

```text
d:/Industry Track Project/
|- .env                              - Local runtime configuration (contains secrets).
|- .env.example                      - Template configuration and defaults.
|- AI_CustomerSupport_PRD.docx       - Word-format PRD artifact.
|- AI_CustomerSupport_PRD.md         - Markdown PRD with architecture and requirements.
|- AI_CustomerSupport_PRD_v2.docx    - Alternate PRD Word artifact.
|- DEMO_PLAN.md                      - Demo script and scenario walkthrough.
|- docker-compose.yml                - Local Redis service definition.
|- PROJECT_SUMMARY.md                - This generated project status report.
|- requirements.txt                  - Python dependency list.
|
|- backend/
|  |- main.py                        - Main FastAPI app, routes, WebSockets, orchestration glue.
|  |- agents/
|  |  |- escalation.py               - Human handoff context-bundle generator.
|  |  |- graph.py                    - LangGraph DAG construction and routing edges.
|  |  |- llm_router.py               - Task-aware model/provider selection.
|  |  |- nodes.py                    - Supervisor/Triage/Resolution/Critic node logic.
|  |  |- state.py                    - Typed state schema shared by LangGraph nodes.
|  |- cache/
|  |  |- response_cache.py           - In-memory TTL response cache and key generation.
|  |- channels/
|  |  |- smtp_client.py              - Optional SMTP sender for email replies.
|  |- db/
|  |  |- mongo.py                    - MongoDB manager (sessions, metrics, analytics).
|  |  |- redis_store.py              - Redis manager (history/meta/profile/queue + fallback).
|  |- rag/
|  |  |- faiss_store.py              - Embeddings, FAISS load/create/retrieve/reindex.
|  |- voice_agent/
|  |  |- __init__.py                 - Voice pipeline exports.
|  |  |- pipeline.py                 - VAD, turn detection, STT and TTS orchestration.
|  |- voice_output/
|     |- *.webm / *.mp3              - Generated temporary voice chunks and TTS outputs.
|
|- faiss_index_shopeasy/
|  |- index.faiss                    - Persisted FAISS vector index.
|  |- index.pkl                      - FAISS metadata/docstore file.
|
|- frontend/
|  |- .gitignore                     - Frontend ignore rules.
|  |- eslint.config.js               - ESLint configuration.
|  |- index.html                     - Vite HTML entrypoint.
|  |- package.json                   - Frontend scripts and dependencies.
|  |- package-lock.json              - Locked npm dependency graph.
|  |- postcss.config.js              - PostCSS configuration.
|  |- README.md                      - Frontend scaffold notes.
|  |- tailwind.config.js             - Tailwind setup.
|  |- vite.config.js                 - Vite bundler config.
|  |- public/
|  |  |- vite.svg                    - Public static asset.
|  |- src/
|     |- App.css                     - Root app CSS overrides.
|     |- App.jsx                     - App shell and view routing.
|     |- index.css                   - Global styles + Tailwind layers.
|     |- main.jsx                    - React mount bootstrap.
|     |- assets/
|     |  |- react.svg                - Local SVG asset.
|     |- components/
|        |- AdminDashboard.jsx       - Admin ops UI.
|        |- ChatWindow.jsx           - Chat + voice-record button support UI.
|        |- ShopEasy.jsx             - Mini-store + cart + support entry point.
|        |- VoiceMode.jsx            - Dedicated streaming voice mode UI.
|
|- kb/
|  |- shopeasy_faq.txt               - RAG knowledge base source text.
```

## 3. What Each File Does (backend/ and frontend/src/)

### Backend Files

`backend/main.py`

- Purpose: Main backend entrypoint and integration hub.
- Key functions/classes:
  - Startup/shutdown: `startup_db`, `shutdown_db`.
  - Voice helpers: `_process_voice_turn`, `_fast_voice_reply`, `_early_voice_reply_preview`.
  - Session/order helpers: `_load_session_history`, `_collect_orders`, `_build_orders_summary`.
  - Profile/order APIs + chat/voice/email endpoints.
  - WebSocket handlers: `/ws/chat/{session_id}`, `/ws/voice-stream/{session_id}`.
- Dependencies: `fastapi`, `whisper`, `pydantic`, `langchain_core`, internal agents/db/cache/rag/voice modules.

`backend/agents/state.py`

- Purpose: Typed state contract for LangGraph.
- Key symbols: `AgentState` typed dict.
- Dependencies: `typing`, `langgraph.graph.message.add_messages`.

`backend/agents/graph.py`

- Purpose: Builds and compiles the multi-agent graph and conditional routing.
- Key symbols: `build_graph`, `app_graph`.
- Dependencies: `langgraph`, `nodes.py`, `state.py`.

`backend/agents/llm_router.py`

- Purpose: Selects model/provider by task and environment availability.
- Key functions: `_has_env`, `_get_ollama_llm`, `get_llm`.
- Dependencies: `dotenv`, `langchain-groq`, `langchain-google-genai`, `langchain-ollama`.

`backend/agents/nodes.py`

- Purpose: Implements Supervisor, Triage, Resolution, and Critic node behavior.
- Key functions:
  - `supervisor_node`, `triage_node`, `resolution_node`, `critic_node`.
  - Retrieval/tool helpers for order details, catalog, and summary.
  - Parsing and heuristic fallback utilities.
- Dependencies: `asyncio`, `httpx`, `langchain_core.messages`, `retrieve_context`, `get_llm`.

`backend/agents/escalation.py`

- Purpose: Generates escalation context bundle for human handoff.
- Key function: `generate_escalation_bundle`.
- Dependencies: `langchain_ollama.ChatOllama`, `dotenv`, `json`.

`backend/cache/response_cache.py`

- Purpose: TTL cache for approved responses; cache key normalization.
- Key symbols: `ResponseCache`, `make_cache_key`, `response_cache` singleton.
- Dependencies: `time`, `threading.Lock`, `re`.

`backend/db/mongo.py`

- Purpose: MongoDB connection and persistence/analytics operations.
- Key methods:
  - `connect_to_mongo`, `append_message`, `log_session_activity`.
  - `get_dashboard_metrics`, `get_live_queue`, `get_analytics_snapshot`, `get_session_history`.
- Dependencies: `motor`, `datetime`, `os`.

`backend/db/redis_store.py`

- Purpose: Redis-backed session memory/meta/profile/email queue manager with fallback profile store.
- Key methods:
  - `append_message`, `get_history`, `set_meta`, `enqueue_email_ticket`.
  - `set_profile`, `get_profile`.
- Dependencies: `redis.asyncio`, `json`, `datetime`.

`backend/rag/faiss_store.py`

- Purpose: Embeddings + FAISS index lifecycle and retrieval.
- Key functions: `initialize_kb`, `retrieve_context`, `append_kb_text`, `reindex_kb`.
- Dependencies: `langchain_community`, `langchain_huggingface`, `FAISS`, `TextLoader`, `RecursiveCharacterTextSplitter`.

`backend/channels/smtp_client.py`

- Purpose: SMTP sending abstraction for email replies.
- Key functions: `_send_sync`, `send_smtp_email`, `_is_enabled`.
- Dependencies: `smtplib`, `email.message`, `asyncio`, `os`.

`backend/voice_agent/pipeline.py`

- Purpose: Voice processing stages (STT/VAD/turn detection/TTS).
- Key classes/functions:
  - `VADResult`, `TurnDecision`, `VoicePipeline`.
  - `transcribe`, `run_vad`, `detect_turn_end`, `synthesize`.
- Dependencies: Whisper model object, `kittentts` (optional), `edge-tts` dynamic import fallback.

`backend/voice_agent/__init__.py`

- Purpose: Re-exports voice pipeline symbols.
- Dependencies: local `pipeline.py`.

Generated files currently present under `backend/`:

- `backend/voice_output/response_*.mp3`: synthesized TTS outputs for recent voice turns.
- `backend/voice_output/stream_*.webm`: captured streamed turn chunks.
- `backend/voice_output/temp_*.webm`: temporary uploaded voice turn files.

### Frontend Files (`frontend/src/`)

`frontend/src/main.jsx`

- Purpose: React app bootstrap.
- Key code: `createRoot(...).render(<App />)`.
- Dependencies: `react`, `react-dom`.

`frontend/src/App.jsx`

- Purpose: Main app shell and navigation between Store/Chat/Voice/Admin views.
- Key component: `App` with sidebar + mobile selector.
- Dependencies: `react`, local components (`ShopEasy`, `ChatWindow`, `VoiceMode`, `AdminDashboard`).

`frontend/src/App.css`

- Purpose: Root-level CSS layout constraints.
- Dependencies: CSS only.

`frontend/src/index.css`

- Purpose: Global styling, Tailwind layers, shared utility component styles.
- Dependencies: Tailwind directives and Google font import.

`frontend/src/components/ChatWindow.jsx`

- Purpose: Real-time support chat UI with optional embedded mode and voice-record upload path.
- Key logic:
  - Loads prior history from `/api/history/{session_id}`.
  - Uses WS chat endpoint for live messaging.
  - Uses `/api/voice/transcribe` for mic-upload turn.
  - Structured rendering for assistant responses.
- Dependencies: `react`, browser `WebSocket`, `MediaRecorder`, `fetch`.

`frontend/src/components/VoiceMode.jsx`

- Purpose: Dedicated streaming voice experience.
- Key logic:
  - WS streaming to `/ws/voice-stream/{session_id}`.
  - Client-side adaptive VAD and automatic turn stop.
  - Displays partial transcript and early reply preview.
  - Plays TTS audio from `/api/voice/audio/{filename}`.
- Dependencies: `react`, browser audio APIs, `WebSocket`, `MediaRecorder`.

`frontend/src/components/ShopEasy.jsx`

- Purpose: Mini e-commerce page (product list/cart/order placement) with support handoff.
- Key logic:
  - Creates mock orders via `/api/mock/order`.
  - Auto-opens chat and sends contextual order message.
  - Cart management and modal confirmations.
- Dependencies: `react`, `fetch`, `WebSocket`, local `ChatWindow`.

`frontend/src/components/AdminDashboard.jsx`

- Purpose: Operations dashboard for sessions/escalations/analytics/KB upload.
- Key logic:
  - Polls `/api/admin/metrics`, `/api/admin/queue`, `/api/admin/analytics`.
  - KB upload via `/api/admin/kb/upload`.
- Dependencies: `react`, `fetch`.

`frontend/src/assets/react.svg`

- Purpose: static SVG asset.
- Dependencies: none.

## 4. Agent Pipeline Status

| Node       | Implemented | Model Path                                                                    | Current Behavior                                                                                                                        |
| ---------- | ----------- | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Supervisor | Yes         | `get_llm(task="routing")` => Groq primary / Gemini fallback / Ollama fallback | Intent classification, complexity/confidence estimate, escalation signal, priority seed.                                                |
| Triage     | Yes         | `get_llm(task="triage")` => Groq primary                                      | Builds subtasks, priority (`P1..P4`), estimated steps, confidence.                                                                      |
| Resolution | Yes         | `get_llm(task="resolution")` => Groq primary                                  | Parallel RAG + order tools (single order/catalog/summary), drafts grounded response, rule-based fast-lane for complaint/delay patterns. |
| Critic     | Yes         | `get_llm(task="critic")` => Gemini primary / Groq fallback / Ollama fallback  | Reviews draft for quality/hallucination/tone and returns `APPROVE/REJECT/ESCALATE`.                                                     |
| Escalation | Yes         | Local `ChatOllama` (`OLLAMA_MODEL`)                                           | Produces context bundle for human handoff queue and escalation logs.                                                                    |

Graph orchestration status: implemented in `backend/agents/graph.py`, with retry path from Critic `REJECT` back to Resolution (max 2 retries), then escalation path.

## 5. API Endpoints Inventory

Status legend:

- `Working`: endpoint implemented and route registration verified.
- `Conditional`: implemented, but runtime success depends on external service/env credentials.

| Method | Path                                | What It Does                                                                                  | Status                                         |
| ------ | ----------------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| GET    | `/`                                 | Health check response.                                                                        | Working                                        |
| GET    | `/api/history/{session_id}`         | Returns session history (Mongo-backed).                                                       | Working                                        |
| GET    | `/api/admin/metrics`                | Active sessions/messages/escalations/recent activity.                                         | Working (degrades if Mongo absent)             |
| GET    | `/api/admin/queue`                  | Escalated sessions queue view.                                                                | Working (degrades if Mongo absent)             |
| GET    | `/api/admin/analytics`              | Intent/priority breakdown + escalation rate.                                                  | Working (degrades if Mongo absent)             |
| POST   | `/api/admin/kb/upload`              | Upload KB text doc and reindex FAISS.                                                         | Working                                        |
| GET    | `/api/mock/order/{order_id}`        | Returns one order detail.                                                                     | Working                                        |
| POST   | `/api/mock/order`                   | Creates/upserts mock order (Mongo or memory fallback).                                        | Working                                        |
| GET    | `/api/mock/orders`                  | Returns order list.                                                                           | Working                                        |
| GET    | `/api/mock/orders/summary`          | Returns aggregate summary; supports session/customer filtering.                               | Working                                        |
| POST   | `/api/session/profile/{session_id}` | Upsert session profile (name/email/phone).                                                    | Working (Redis-backed with in-memory fallback) |
| GET    | `/api/session/profile/{session_id}` | Fetch session profile.                                                                        | Working (Redis-backed with in-memory fallback) |
| GET    | `/api/mock/order/{order_id}/events` | Fetch order event timeline.                                                                   | Working                                        |
| POST   | `/api/mock/order/{order_id}/event`  | Append order event and status update.                                                         | Working                                        |
| WS     | `/ws/chat/{session_id}`             | Real-time chat socket using LangGraph pipeline + caching.                                     | Working                                        |
| POST   | `/api/voice/transcribe`             | Upload voice turn, STT -> pipeline -> TTS URL response.                                       | Working                                        |
| POST   | `/api/email/inbound`                | Email intake through same support flow, optional SMTP outbound.                               | Conditional (SMTP depends on creds)            |
| WS     | `/ws/voice-stream/{session_id}`     | Streaming voice chunks, auto-turn detection, partial transcript, early preview, final result. | Working                                        |
| GET    | `/api/voice/audio/{filename}`       | Serves generated TTS audio file.                                                              | Working (file must exist)                      |

## 6. Database & Memory Status

### MongoDB

- Connection behavior: attempts `MONGO_URI` or fallback `mongodb://127.0.0.1:27017` at startup.
- Current runtime status in this report: not guaranteed from static analysis; code handles failures gracefully.
- Collections used:
  - `support_sessions` (history, session activity, escalation data, analytics aggregation).
  - `orders` (mock order records and timeline events, when DB available).

### Redis

- Connection behavior: attempts `REDIS_URL` at startup.
- Current runtime status in this report: not guaranteed; code falls back for profile memory when unavailable.
- Data structures/keys used:
  - `session:{id}:history` (list)
  - `session:{id}:meta` (hash)
  - `session:{id}:profile` (hash or in-memory fallback)
  - `support:email:queue` (list)

### FAISS / RAG

- Index directory present: `faiss_index_shopeasy/` with `index.faiss` and `index.pkl`.
- Documents loaded from: `kb/shopeasy_faq.txt`.
- Behavior:
  - `initialize_kb()` loads existing index or creates one.
  - `append_kb_text()` appends text and reindexes.

## 7. Frontend Components Status

| Component/File                  | What It Renders                                                                               | APIs/WS Used                                                                                              | Status  |
| ------------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------- |
| `App.jsx`                       | Main layout + navigation between Store/Chat/Voice/Admin.                                      | none directly                                                                                             | Working |
| `components/ShopEasy.jsx`       | Product cards, cart drawer, order modal, floating support launcher.                           | `POST /api/mock/order`, `WS /ws/chat/{session_id}`                                                        | Working |
| `components/ChatWindow.jsx`     | Live chat conversation UI and mic-record upload control.                                      | `GET /api/history/{session_id}`, `WS /ws/chat/{session_id}`, `POST /api/voice/transcribe`                 | Working |
| `components/VoiceMode.jsx`      | Dedicated voice page with auto listening, VAD state, partial transcript/early preview panels. | `WS /ws/voice-stream/{session_id}`, `GET /api/voice/audio/{filename}`                                     | Working |
| `components/AdminDashboard.jsx` | Metrics cards, live escalation queue, analytics breakdown, KB upload.                         | `GET /api/admin/metrics`, `GET /api/admin/queue`, `GET /api/admin/analytics`, `POST /api/admin/kb/upload` | Working |
| `main.jsx`                      | React bootstrapping.                                                                          | none                                                                                                      | Working |
| `index.css`, `App.css`          | Global and root styles.                                                                       | none                                                                                                      | Working |

## 8. Environment Variables (`.env.example`)

Legend:

- `Filled`: has non-empty default/sample value.
- `Empty`: blank and must be provided for full functionality.

| Variable                            | Value in `.env.example`  | Status |
| ----------------------------------- | ------------------------ | ------ |
| `GROQ_API_KEY`                      | empty                    | Empty  |
| `GROQ_MODEL`                        | `openai/gpt-oss-120b`    | Filled |
| `VOICE_GROQ_MODEL`                  | `openai/gpt-oss-120b`    | Filled |
| `EMAIL_GROQ_MODEL`                  | `openai/gpt-oss-120b`    | Filled |
| `GEMINI_API_KEY`                    | empty                    | Empty  |
| `GEMINI_MODEL`                      | `gemini-1.5-flash`       | Filled |
| `OLLAMA_MODEL`                      | `llama3.2:3b`            | Filled |
| `TTS_ENGINE`                        | `kitten`                 | Filled |
| `KITTEN_TTS_VOICE`                  | `Jasper`                 | Filled |
| `EDGE_TTS_VOICE`                    | `en-IN-NeerjaNeural`     | Filled |
| `META_WHATSAPP_TOKEN`               | empty                    | Empty  |
| `META_PHONE_NUMBER_ID`              | empty                    | Empty  |
| `META_VERIFY_TOKEN`                 | `random_string_12345`    | Filled |
| `MONGO_URI`                         | empty                    | Empty  |
| `REDIS_URL`                         | `redis://localhost:6379` | Filled |
| `REDIS_SESSION_TTL_SECONDS`         | `86400`                  | Filled |
| `EMAIL_CHANNEL_ENABLED`             | `true`                   | Filled |
| `SUPPORT_EMAIL_FROM`                | `support@shopeasy.local` | Filled |
| `VOICE_FAST_MODE`                   | `true`                   | Filled |
| `VOICE_STREAM_SILENCE_SEC`          | `1.0`                    | Filled |
| `VOICE_STREAM_MIN_BYTES`            | `3000`                   | Filled |
| `VOICE_STREAM_PARTIAL_ENABLED`      | `true`                   | Filled |
| `VOICE_STREAM_PARTIAL_INTERVAL_SEC` | `0.85`                   | Filled |
| `VOICE_STREAM_PARTIAL_MIN_BYTES`    | `9000`                   | Filled |
| `EMAIL_SMTP_ENABLED`                | `true`                   | Filled |
| `SMTP_HOST`                         | `smtp.gmail.com`         | Filled |
| `SMTP_PORT`                         | `587`                    | Filled |
| `SMTP_USER`                         | empty                    | Empty  |
| `SMTP_PASS`                         | empty                    | Empty  |
| `SMTP_USE_TLS`                      | `true`                   | Filled |
| `SMTP_FROM_EMAIL`                   | `support@shopeasy.local` | Filled |

## 9. Known Issues & Bugs

### Observed During Implementation/Testing

- SMTP outbound is configured but likely non-operational until `SMTP_USER` and `SMTP_PASS` are provided.
- Mongo/Redis connectivity is environment-dependent; when unavailable, parts of persistence/analytics degrade.
- Voice pipeline may incur first-turn cold-start latency due to Whisper/model initialization.
- Voice output/temp files accumulate in `backend/voice_output` (no cleanup policy yet).

### Half-Working / Conditional Features

- Email channel is functionally complete for inbound processing, but outbound delivery success is credential-dependent.
- Session profile personalization works with Redis and has in-memory fallback, but fallback is process-local only (not shared across instances/restarts).

### Integration Gaps

- Order system remains mock/local; no real upstream OMS/e-commerce API integration yet.
- No auth guard for admin endpoints.

## 10. What's Left To Build

| Remaining Task                      | Description                                                                        | Complexity |
| ----------------------------------- | ---------------------------------------------------------------------------------- | ---------- |
| Real external order/CRM integration | Replace mock order endpoints with real APIs + retries + schema mapping.            | Hard       |
| Authentication & authorization      | Add JWT/session auth and role checks for admin and sensitive routes.               | Medium     |
| End-to-end automated tests          | Add backend unit/integration tests + frontend component/e2e tests.                 | Medium     |
| CI/CD pipeline                      | Add lint/test/build/deploy workflows and environment promotion strategy.           | Medium     |
| Observability                       | Structured logs, tracing, metrics dashboard, alerting for failures/latency.        | Medium     |
| Data governance/security hardening  | Secret management, PII handling, encryption posture, input abuse protection.       | Hard       |
| Cleanup and retention policies      | Periodic cleanup for voice temp/audio files and cache pruning rules.               | Easy       |
| Queue-backed async workers          | Move heavy tasks (reindexing, email retries, long summarizations) to worker queue. | Medium    
| `SMTP_USE_TLS` | `true` | Filled |
| `SMTP_FROM_EMAIL` | `support@shopeasy.local` | Filled |

## 9. Known Issues & Bugs

### Observed During Implementation/Testing

- SMTP outbound is configured but likely non-operational until `SMTP_USER` and `SMTP_PASS` are provided.
- Mongo/Redis connectivity is environment-dependent; when unavailable, parts of persistence/analytics degrade.
- Voice pipeline may incur first-turn cold-start latency due to Whisper/model initialization.
- Voice output/temp files accumulate in `backend/voice_output` (no cleanup policy yet).

### Half-Working / Conditional Features

- Email channel is functionally complete for inbound processing, but outbound delivery success is credential-dependent.
- Session profile personalization works with Redis and has in-memory fallback, but fallback is process-local only (not shared across instances/restarts).

### Integration Gaps

- Order system remains mock/local; no real upstream OMS/e-commerce API integration yet.
- No auth guard for admin endpoints.

## 10. What's Left To Build

| Remaining Task | Description | Complexity |
|---|---|---|
| Real external order/CRM integration | Replace mock order endpoints with real APIs + retries + schema mapping. | Hard |
| Authentication & authorization | Add JWT/session auth and role checks for admin and sensitive routes. | Medium |
| End-to-end automated tests | Add backend unit/integration tests + frontend component/e2e tests. | Medium |
| CI/CD pipeline | Add lint/test/build/deploy workflows and environment promotion strategy. | Medium |
| Observability | Structured logs, tracing, metrics dashboard, alerting for failures/latency. | Medium |
| Data governance/security hardening | Secret management, PII handling, encryption posture, input abuse protection. | Hard |
| Cleanup and retention policies | Periodic cleanup for voice temp/audio files and cache pruning rules. | Easy |
| Queue-backed async workers | Move heavy tasks (reindexing, email retries, long summarizations) to worker queue. | Medium |

---

### Final Assessment

The project is in a strong, near-demo-complete state for an agentic AI customer care system: multi-agent orchestration, RAG, voice streaming, admin analytics, and multi-channel handling are all implemented. The primary remaining work is productionization (security, testing, external integrations, operations hardening), not core feature creation.
