# Project Context Document: AI-Powered Customer Support System

## 1. Project Overview
This project is a production-grade, multi-agent AI customer support platform designed to autonomously handle Tier-1 and Tier-2 customer queries across chat, email, and voice channels. 

**The core problem it solves:** It significantly reduces support ticket backlog and improves resolution times by instantly answering common queries (order tracking, refunds, FAQs). More importantly, it seamlessly escalates complex or sensitive issues to human agents, providing them with a concise, AI-generated summary bundle so customers never have to repeat themselves.

**Who the end user is:** The primary end users are customers of an e-commerce platform (e.g., ShopEasy) needing quick support. The secondary users are human customer service agents and administrators who use the admin dashboard to manage escalations, monitor system analytics, and update the knowledge base.

---

## 2. Tech Stack
- **Frontend:** React 19, Vite, Tailwind CSS, Socket.IO (Client), Web Audio API.
- **Backend:** Python, FastAPI, LangGraph (for agent orchestration), LangChain, WebSockets, Python `smtplib`.
- **Database / Storage:** MongoDB Atlas (persistent chat history, ticket logs, metrics), Redis (short-term session state, rate limiting, queues).
- **AI/ML Components:**
  - **LLM Providers:** Groq API (Llama-3.3-70b), Google Gemini 1.5 Flash, Ollama (local Llama 3.2 3B).
  - **Voice Models:** OpenAI Whisper (Base, local STT), Edge-TTS (Neural TTS).
  - **Vector DB / Embeddings:** FAISS, HuggingFace `all-MiniLM-L6-v2` embeddings.
- **Infrastructure / Deployment:** Docker, Docker Compose (for local Redis/services), Uvicorn.

---

## 3. Architecture
The system utilizes a 5-tier architecture:
1. **Ingestion Layer:** Multi-channel endpoints (WebSockets for chat/voice streaming, REST for mock tickets) normalize incoming messages into a unified schema.
2. **Orchestration Layer:** A LangGraph state machine manages a Directed Acyclic Graph (DAG) of 6 specialized agents. The Supervisor node acts as the entry router.
3. **Intelligence Layer:** A dynamic LLM router selects the best model per task (e.g., Groq for speed, Gemini for review, Ollama for local offline tasks). Retrieval-Augmented Generation (RAG) is executed via FAISS.
4. **Memory Layer:** Redis handles immediate session state and TTL, while MongoDB stores persistent customer history and analytics.
5. **Delivery Layer:** Formats the final approved response and streams it back via WebSocket, or converts it to audio via TTS.

**Notable Design Decisions:** 
- **The Critic Agent:** Before any message reaches the user, an independent Critic Agent reviews the draft for factual accuracy, tone, and hallucination. If rejected, the Resolution Agent is forced to retry.
- **Hybrid LLM Routing:** To optimize for latency and data privacy, the system routes tasks based on requirements (e.g., local Ollama is used exclusively for summarizing private chat logs during human escalation).

---

## 4. Features Built
- **Multi-Agent Orchestration:** A LangGraph DAG with 6 specialized agents (Supervisor, Triage, Resolution, Critic, Escalation, Voice) collaborating to process intents and sub-tasks.
- **RAG-Powered Resolution:** FAISS vector search retrieves relevant policy/FAQ chunks to ground agent responses, effectively mitigating LLM hallucinations.
- **Streaming Voice Support Pipeline:** End-to-end voice processing using Whisper (STT) and Edge-TTS, featuring VAD (Voice Activity Detection), partial transcripts, and early reply previews.
- **Automated Human Handoff (Context Bundle):** An offline local LLM generates a concise, 50-word conversation summary and sentiment analysis when escalating an issue to the live admin queue.
- **Adversarial Critic QA Loop:** An independent agent loop that strictly evaluates drafted responses, forcing a self-correction retry if quality standards are not met.
- **Real-Time Admin Dashboard:** A live React interface displaying active sessions, escalation queues, MongoDB-backed analytics, and a drag-and-drop RAG Knowledge Base uploader.

---

## 5. My Contribution (What I Built)
As the sole developer on this project, I architected and implemented the entire system end-to-end. Specific contributions include:
- **Graph Orchestration (`backend/agents/graph.py`, `nodes.py`):** Designed the LangGraph state machine, enforcing strict JSON output schemas for reliable transitions between the Supervisor, Triage, and Resolution nodes.
- **Hybrid LLM Router (`backend/agents/llm_router.py`):** Built a custom wrapper to dynamically swap between `langchain-groq`, `langchain-google-genai`, and `langchain-ollama` based on the active agent task.
- **Voice Pipeline (`backend/voice_agent/pipeline.py`):** Developed the streaming audio pipeline, handling raw chunks via WebSockets, transcribing them with local Whisper, and synthesizing the final response using Edge-TTS.
- **RAG Implementation (`backend/rag/faiss_store.py`):** Integrated HuggingFace embeddings and FAISS, including logic for document chunking, dynamic re-indexing, and similarity search.
- **Full-Stack UI:** Built the entire React frontend (`ChatWindow.jsx`, `VoiceMode.jsx`, `AdminDashboard.jsx`), managing complex WebSocket connection states and live metric polling.

---

## 6. Challenges & Solutions
- **Challenge: LLM Hallucinations and Incorrect Policies.** Early iterations of the agent would confidently invent non-existent refund policies or fake order numbers.
  - **Solution:** I implemented a two-part fix: 1) Strict RAG grounding (the prompt forbids answering without citing the retrieved FAISS chunk) and 2) The "Critic Agent" pattern, which independently double-checks the draft against the retrieved context and forces a retry if it detects a hallucination.
- **Challenge: Voice Channel Latency.** Users experienced high perceived latency waiting for the full STT -> LLM -> TTS pipeline to finish.
  - **Solution:** I moved the primary reasoning engine to Groq (Llama-3.3-70b) for ultra-low inference latency. I also implemented partial transcripts and UI thinking states on the frontend to provide immediate visual feedback while the audio was synthesizing.
- **Challenge: Maintaining Context During Escalations Securely.** Passing full chat transcripts to external LLMs for summarization posed a data privacy concern and wasted API tokens.
  - **Solution:** I deployed a local, offline instance of Ollama (Llama 3.2 3B). When an escalation is triggered, this local model runs on the host machine to read the chat history and generate a secure "Context Bundle" for the human agent.

---

## 7. AI/ML Specifics
- **Model Selection:**
  - **Groq (Llama-3.3-70b):** Used for Supervisor, Triage, and Resolution due to its industry-leading tokens-per-second speed, which is critical for real-time chat and voice.
  - **Gemini 1.5 Flash:** Used for the Critic agent. It excels at fast, reliable classification and evaluation tasks.
  - **Ollama (Llama 3.2 3B):** Used for the Escalation agent to guarantee that sensitive session summaries never leave the local infrastructure.
- **RAG Strategy:** Documents are parsed and chunked using LangChain's `RecursiveCharacterTextSplitter` (512 token chunks, 64 token overlap to preserve semantic context). Embeddings are generated locally using the `all-MiniLM-L6-v2` HuggingFace model and stored in a persistent FAISS index.
- **Prompt Engineering:**
  - **Chain-of-Thought (CoT):** Applied to the Triage agent (e.g., *"First identify the root cause, then list each sub-task required, then assign a priority"*).
  - **Adversarial Prompting:** Used for the Critic agent to ensure it actively searches for flaws rather than acting as a rubber stamp.

---

## 8. What I Would Improve
- **Known Limitations:** 
  - The order management integration is currently mocked. 
  - The local Whisper STT can suffer from cold-start latency on the very first audio turn before the model is fully loaded into memory.
  - Voice output generation using Edge-TTS requires an internet connection; a fully local TTS solution (like KittenTTS or Coqui) would make the system 100% offline-capable.
- **What I'd do differently with more time:**
  - **Real External Integrations:** Connect the tool nodes to real REST APIs (e.g., Shopify for orders, Zendesk for ticketing).
  - **Dedicated Intent Classifier:** Instead of using an LLM for the initial Supervisor routing, I would train or fine-tune a lightweight BERT classifier. This would save tokens, drastically reduce initial latency, and handle massive concurrency better.
  - **Automated Testing:** Implement a comprehensive suite of unit, integration, and e2e tests alongside a CI/CD pipeline for production readiness.
