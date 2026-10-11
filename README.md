# ShopEasy AI Customer Support

ShopEasy is a full-stack AI customer support prototype for chat, voice, order assistance, knowledge-base retrieval, and admin operations. It combines a React/Vite frontend with a FastAPI backend, LangGraph agent orchestration, FAISS retrieval, Redis session state, and optional MongoDB persistence.

## Features

- Multi-agent support flow with Supervisor, Triage, Resolution, Critic, and Escalation behavior
- Real-time chat over WebSockets
- Voice support with Whisper speech-to-text and text-to-speech output
- FAISS-based retrieval over the ShopEasy FAQ knowledge base
- Mock order lookup, order history, order events, and order creation
- Admin metrics, queue, analytics, and knowledge-base upload endpoints
- Provider-aware LLM routing for Groq, Gemini, and Ollama
- Redis-backed session state with local fallback behavior
- Optional MongoDB persistence and SMTP email channel

## Architecture

```text
React/Vite frontend
        |
        | REST + WebSocket
        v
FastAPI backend
        |
        +-- LangGraph agent workflow
        +-- LLM router: Groq / Gemini / Ollama
        +-- FAISS knowledge retrieval
        +-- Redis session state
        +-- MongoDB persistence (optional)
        +-- Whisper + TTS voice pipeline
```

## Repository Layout

```text
backend/                 FastAPI app, agents, RAG, storage, and voice pipeline
frontend/                React/Vite application
kb/                      Knowledge-base source files
faiss_index_shopeasy/    Persisted FAISS index and metadata
.env.example             Environment variable template
requirements.txt         Python dependencies
docker-compose.yml       Local Redis service
```

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer and npm
- Docker Desktop, recommended for local Redis
- API credentials for the LLM provider you want to use
- Optional: MongoDB, SMTP credentials, and Ollama for additional integrations

## Setup

### 1. Clone and enter the project

```bash
git clone https://github.com/Vishwa-247/AI_CustomerSupport.git
cd AI_CustomerSupport
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in the credentials required for your selected providers.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`. It is excluded by `.gitignore`.

### 3. Create the Python environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Start Redis

```bash
docker compose up -d redis
```

Redis is used for session state. The backend also supports limited in-memory fallback behavior for local development.

### 5. Start the backend

From the repository root, with the virtual environment active:

```bash
uvicorn backend.main:app --reload --port 8000
```

The API is available at `http://localhost:8000` and interactive API documentation is available at `http://localhost:8000/docs`.

### 6. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.

## Main Endpoints

| Area | Endpoint |
|---|---|
| Health/root | `GET /` |
| Chat history | `GET /api/history/{session_id}` |
| Chat WebSocket | `ws://localhost:8000/ws/chat/{session_id}` |
| Voice WebSocket | `ws://localhost:8000/ws/voice-stream/{session_id}` |
| Voice transcription | `POST /api/voice/transcribe` |
| Order lookup | `GET /api/mock/order/{order_id}` |
| Order list | `GET /api/mock/orders` |
| Admin metrics | `GET /api/admin/metrics` |
| Admin queue | `GET /api/admin/queue` |
| Admin analytics | `GET /api/admin/analytics` |
| Knowledge-base upload | `POST /api/admin/kb/upload` |

See `/docs` for the complete generated API schema.

## Knowledge Base

The default FAQ source is `kb/shopeasy_faq.txt`. The persisted FAISS files are stored in `faiss_index_shopeasy/`. The backend initializes the index during startup and exposes an admin upload endpoint for appending new knowledge-base content.

## Development Commands

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Backend:

```bash
python -m compileall backend
```

## Current Scope and Limitations

This repository is a working prototype and demo foundation rather than a production deployment. Order tools currently use mock or local data. Production authentication, role-based admin authorization, automated test coverage, CI/CD, observability, and integrations with real CRM/order systems still need to be added before production use.

## Security Notes

- Keep `.env` private and use `.env.example` as the shareable configuration template.
- Replace development CORS settings before production deployment.
- Add authentication and authorization before exposing admin endpoints publicly.
- Treat uploaded knowledge-base content and generated voice files as runtime data.

## License

No license has been specified for this project yet.
