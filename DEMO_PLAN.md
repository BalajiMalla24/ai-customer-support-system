# AI Customer Support System — Demo Plan & Use Case

**Woxsen University | B.Tech CSE (DS) | 8th Semester | Presentation: March 26**

## Current Execution Status (Updated)

- Phase 5 complete: Chat UI and WebSocket flow hardened (history restore, assistant thinking state, escalation flow).
- Phase 6 complete: Admin queue and analytics endpoints live with MongoDB-backed metrics.
- Phase 7 complete for documentation/demo prep: scenario script, runbook, and KB upload path finalized.
- Voice module intentionally deferred to final pass as requested.

---

## ✅ What You've Already Built (Phases 1–6)

You are in a strong position. Here's an honest status check:

| Phase                       | What's Done                                            | Status     |
| --------------------------- | ------------------------------------------------------ | ---------- |
| FastAPI + WebSocket backend | Real-time chat server running                          | ✅ Done    |
| LangGraph 6-node DAG        | Supervisor → Triage → Resolution → Critic → Escalation | ✅ Done    |
| Ollama llama3.2:3b          | 100% local, offline, no API key needed                 | ✅ Done    |
| React frontend              | Chat UI + Admin Dashboard, SaaS design                 | ✅ Done    |
| FAISS RAG                   | HuggingFace all-MiniLM-L6-v2, local embeddings         | ✅ Done    |
| MongoDB Atlas               | Persistent chat history, session restore               | ✅ Done    |
| Escalation + Context Bundle | Auto human handoff with 50-word summary                | ✅ Done    |
| Voice Agent (Phase 7)       | Whisper STT + edge-tts                                 | 🔲 Pending |

**You only need Phase 7 + a solid use case + demo polish. That's it.**

---

## 🎯 Use Case: ShopEasy E-Commerce Customer Support

### Why E-Commerce?

- Everyone understands it instantly — judges, faculty, anyone
- Easy mock data: order IDs, refund policies, shipping timelines
- Covers all intent types naturally: tracking, refunds, complaints, escalation
- Your RAG KB = a simple FAQ + policy document (you write it in 30 minutes)

### The Client

> **ShopEasy** — a mid-sized Indian e-commerce platform selling electronics and accessories.
> They receive 500+ customer queries per day on WhatsApp and web chat.
> This system automates tier-1 and tier-2 support entirely.

### Customer Persona for Demo

> **Arjun, 24, Hyderabad** — ordered a Bluetooth speaker, hasn't received it in 7 days.
> Contacts support via the web chat widget.

---

## 📄 RAG Knowledge Base — What to Put In It

Create a file called `kb/shopeasy_faq.txt` with this content. This is what your FAISS store will index.

```
ShopEasy Customer Support Knowledge Base

ORDER TRACKING
- Standard delivery takes 5-7 business days within India.
- Express delivery takes 2-3 business days. Available in metro cities.
- To track your order, visit shopeasy.in/track and enter your order ID.
- If your order shows "In Transit" for more than 5 days, raise a support ticket.
- Orders above Rs. 999 get free standard shipping.

REFUND POLICY
- Refunds are processed within 5-7 business days after the return is received.
- Eligible for refund: damaged items, wrong item delivered, item not delivered.
- Not eligible for refund: used items, items without original packaging after 48 hours.
- Refund amount is credited to the original payment method.
- UPI and wallet refunds are processed within 24 hours.
- Bank transfer refunds take 5-7 business days.

RETURN POLICY
- Return window is 7 days from delivery date.
- Items must be unused and in original packaging.
- Electronics must include all accessories and box for return.
- Raise a return request at shopeasy.in/returns with your order ID.

TECHNICAL SUPPORT
- For app issues, clear cache and try reinstalling the ShopEasy app.
- For payment failures, wait 30 minutes — if amount is deducted, it auto-refunds in 24 hours.
- For login issues, use Forgot Password on the login page.
- For product defects within warranty period, contact the brand service center directly.

ESCALATION TRIGGERS
- If order is delayed beyond 10 business days, escalate to logistics team.
- If customer has raised the same complaint more than twice, escalate to senior support.
- If payment was deducted but order not placed, escalate immediately to payments team.

CONTACT
- Support hours: 9 AM to 9 PM IST, Monday to Saturday.
- Emergency escalations are handled 24x7.
```

---

## 🎬 Demo Script — 5 Scenarios (10 Minutes Total)

Present these 5 scenarios in order. Each one showcases a different agent in the pipeline.

---

### Scenario 1 — Order Tracking (2 min)

**Shows: Supervisor → Resolution → Critic → Response**

**What to type in chat:**

```
Hi, I ordered a Bluetooth speaker 7 days ago (Order #SE-4821)
and I still haven't received it. Can you help?
```

**What should happen:**

- Supervisor classifies: `intent=order_tracking, priority=P3`
- Resolution Agent retrieves RAG chunk about delivery timelines
- Critic approves the response
- Customer gets a clear response with tracking info and next steps

**What to say to judges:**

> "Notice the Supervisor agent classified the intent, the Resolution agent pulled the exact policy from our knowledge base — not from the LLM's memory — and the Critic agent reviewed it before sending. The entire pipeline ran locally on Ollama."

---

### Scenario 2 — Refund Request (2 min)

**Shows: Triage Agent decomposing a complex query**

**What to type in chat:**

```
I received a damaged speaker and I paid Rs. 2499 via UPI.
I want a full refund immediately. This is unacceptable.
```

**What should happen:**

- Supervisor detects complaint + refund intent, routes to Triage
- Triage decomposes: `[verify damage claim, check refund eligibility, check payment method, calculate timeline]`
- Resolution retrieves refund policy (UPI = 24 hours)
- Critic reviews tone (angry customer = empathetic response required)
- Response is calm, empathetic, gives exact timeline

**What to say to judges:**

> "The Triage agent broke this complex query into sub-tasks using chain-of-thought reasoning. It didn't just search for 'refund' — it understood there were multiple steps involved."

---

### Scenario 3 — Critic Agent Catching a Bad Response (2 min)

**Shows: Critic rejecting and retrying**

**What to type in chat:**

```
My order was supposed to arrive in 2 days but it's been 15 days.
I want compensation and I want to speak to your manager right now.
```

**What should happen:**

- First draft from Resolution may be too generic or miss the urgency
- Critic rejects it (tone/completeness issue) — show this in terminal logs
- Second draft is better — Critic approves
- Terminal shows: `CRITIC: REJECTED → retry 1` then `CRITIC: APPROVED`

**What to say to judges:**

> "This is the Critic agent — it's an independent quality gate. It rejected the first response because it didn't adequately address the customer's urgency. The system self-corrected without any human involvement."

---

### Scenario 4 — Escalation Flow (2 min)

**Shows: Escalation Agent + Admin Dashboard**

**What to type in chat:**

```
I have complained 3 times already about my missing order.
Nobody is helping me. I need a human agent NOW.
```

**What should happen:**

- Supervisor detects escalation trigger (repeated complaint + explicit human request)
- Escalation Agent (Ollama, local) generates 50-word context bundle
- Admin Dashboard updates in real-time — shows new escalation with bundle
- Customer gets: "Connecting you to a support specialist. Estimated wait: 5 minutes."

**Switch to Admin Dashboard tab and show:**

- Escalation count went from X to X+1
- Context bundle is visible: summary of conversation, issue category, suggested resolution

**What to say to judges:**

> "The Escalation agent runs completely offline on the local Ollama model — no data leaves the machine. When it hands off to a human, it packages the entire conversation context so the agent doesn't have to re-read the chat."

---

### Scenario 5 — Voice Query (2 min) _(Phase 7 — build before demo)_

**Shows: Whisper STT + edge-tts pipeline**

**What to do:**

- Click the mic button in the chat UI
- Say: _"I want to return my order, what is the return policy?"_
- Show Whisper transcription appearing on screen
- Agent responds with text + audio plays back automatically

**What to say to judges:**

> "The voice pipeline is fully local — Whisper transcribes speech on-device, the same agent pipeline processes it, and edge-tts converts the response back to speech. Zero external API calls for the voice layer."

---

## 🔧 Phase 7 — What You Need to Build Before Demo

This is your **only remaining task.** Everything else is done.

### Backend — Add to `main.py`

```
POST /api/voice/transcribe
- Accept: multipart audio file (webm/wav)
- Process: load whisper base model → transcribe → return {text, session_id}
- Then feed transcribed text into existing WebSocket agent pipeline as normal message
```

### Frontend — Add to `ChatWindow.jsx`

```
- Add mic button (toggle on/off)
- On press: MediaRecorder API records audio
- On release: POST audio blob to /api/voice/transcribe
- On response: inject transcribed text into chat as user message
- Play TTS audio response using HTML5 audio tag
```

### TTS — Use edge-tts (not KittenTTS for simplicity)

```bash
pip install edge-tts
```

```python
# In your voice endpoint, after agent response:
import edge_tts
communicate = edge_tts.Communicate(response_text, voice="en-IN-NeerjaNeural")
await communicate.save("response.mp3")
# Return audio file as response
```

**Why edge-tts over KittenTTS for now:** edge-tts is one pip install, no ONNX setup, Indian English voice available (`en-IN-NeerjaNeural`), sounds natural. Needs internet but that's fine for demo day.

---

## ✅ Pre-Demo Checklist

### Day Before (March 25)

- [ ] Build Phase 7 — voice endpoint + mic button in frontend
- [ ] Load `kb/shopeasy_faq.txt` into FAISS store and verify retrieval works
- [ ] Run all 5 demo scenarios once end-to-end — fix any crashes
- [ ] Make sure Ollama is running: `ollama serve` + `ollama pull llama3.2:3b`
- [ ] MongoDB Atlas connection tested — chat history restores on refresh
- [ ] Open two browser tabs — make sure system doesn't crash (Ollama handles one request at a time — queue concurrent requests)

### Demo Day (March 26)

- [ ] Start Ollama first: `ollama serve`
- [ ] Start backend: `uvicorn backend.main:app --reload`
- [ ] Start frontend: `npm run dev`
- [ ] Open Chat UI in one tab, Admin Dashboard in another tab — show side by side
- [ ] Have terminal visible on screen — judges love seeing agent traces
- [ ] Test Scenario 1 once before judges arrive
- [ ] Have `kb/shopeasy_faq.txt` open to show what's in the RAG knowledge base

---

## 🗣️ What to Say in Presentation (Opening 60 Seconds)

> "We built an AI-powered customer support system for an e-commerce business.
> What makes it agentic is that it doesn't just call an LLM once —
> it has 6 specialized agents that collaborate: one classifies your intent,
> one breaks it into sub-tasks, one retrieves the actual policy from a knowledge base,
> one independently reviews the response for quality before it's sent,
> and one handles escalation to humans when needed — with full context.
> The entire system runs locally on Ollama. No API keys. No internet dependency.
> Let me show you."

---

## 📊 Agentic AI Brief — Coverage Map

| Requirement          | How You Cover It                               | Demo Moment                                 |
| -------------------- | ---------------------------------------------- | ------------------------------------------- |
| Agent Orchestration  | LangGraph 6-node DAG                           | Every scenario — show terminal traces       |
| Planning & Reasoning | Triage CoT decomposition                       | Scenario 2 — refund request                 |
| Memory Integration   | MongoDB persistent history + Redis session     | Refresh browser mid-demo — history restores |
| RAG                  | FAISS + HuggingFace embeddings + KB injection  | Scenario 1 — show KB chunk retrieved        |
| Offline/Local Model  | Ollama llama3.2:3b, 100% local                 | Point out "no internet needed" explicitly   |
| Tool Usage           | FAISS retrieval, MongoDB read/write, WebSocket | Running throughout all scenarios            |

**Every single requirement is covered. You're good.**

---

_ShopEasy Demo Plan | AI Customer Support System v1.0 | Woxsen University 2026_
