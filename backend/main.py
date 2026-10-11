import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import whisper
from dotenv import load_dotenv
from fastapi import (FastAPI, File, Form, HTTPException, UploadFile, WebSocket,
                     WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.agents.escalation import generate_escalation_bundle
from backend.agents.llm_router import get_llm
from backend.cache.response_cache import make_cache_key, response_cache
from backend.channels.smtp_client import send_smtp_email
from backend.db.mongo import db_manager
from backend.db.redis_store import redis_manager
from backend.rag.faiss_store import (append_kb_text, initialize_kb,
                                     retrieve_context)
from backend.voice_agent import VoicePipeline

load_dotenv()

app = FastAPI(title="AI Customer Support - Local Web Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

whisper_model = None
voice_pipeline: VoicePipeline | None = None
in_memory_orders: dict[str, dict] = {}
ORDER_ID_REGEX = r"(SE-\d{4})"


def _extract_order_id_from_text(text: str | None) -> str:
    if not text:
        return ""
    order_match = re.search(ORDER_ID_REGEX, text.upper())
    return order_match.group(1) if order_match else ""


async def _resolve_order_context(session_id: str, user_text: str | None = None, explicit_order_id: str | None = None) -> str:
    explicit = str(explicit_order_id or "").strip().upper()
    if explicit and not re.fullmatch(ORDER_ID_REGEX, explicit):
        explicit = ""

    from_text = _extract_order_id_from_text(user_text)
    if explicit or from_text:
        order_id = explicit or from_text
        await redis_manager.set_profile(session_id, {"order_id": order_id})
        return order_id

    profile = await redis_manager.get_profile(session_id)
    profile_order = str(profile.get("order_id") or "").strip().upper()
    if profile_order and re.fullmatch(ORDER_ID_REGEX, profile_order):
        return profile_order

    return ""

@app.on_event("startup")
async def startup_db():
    await db_manager.connect_to_mongo()
    await redis_manager.connect()
    
    print("\n[STARTUP] Pre-loading RAG FAISS Index and Embeddings...")
    initialize_kb()
    
    global whisper_model
    global voice_pipeline
    print("[STARTUP] Pre-loading OpenAI Whisper base model...")
    whisper_model = whisper.load_model("base")
    voice_pipeline = VoicePipeline(whisper_model)
    print("[STARTUP] All models loaded successfully.\n")

@app.on_event("shutdown")
async def shutdown_db():
    await db_manager.close_mongo_connection()
    await redis_manager.close()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        # Ensure session exists in DB
        await db_manager.log_session_activity(session_id)

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)

manager = ConnectionManager()


class MockOrderCreate(BaseModel):
    order_id: str
    product_name: str
    price: int
    customer_name: str
    quantity: int = 1
    status: str = "In Transit"
    eta_days: int = 5
    session_id: str | None = None


class OrderEventCreate(BaseModel):
    status: str
    note: str = ""


class SessionProfileUpdate(BaseModel):
    customer_name: str | None = None
    email: str | None = None
    phone: str | None = None


def _as_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _builtin_orders() -> dict[str, dict]:
    return {
        "SE-4821": {
            "item": "Bluetooth Speaker",
            "price": 2499,
            "quantity": 1,
            "status": "In Transit",
            "ordered": "7 days ago",
            "estimated_delivery": "tomorrow",
            "customer": "Arjun",
            "ordered_at": "2026-03-19T10:30:00Z",
            "events": [
                {"status": "Order Placed", "note": "Payment captured.", "timestamp": "2026-03-19T10:30:00Z"},
                {"status": "Dispatched", "note": "Shipped from Bengaluru hub.", "timestamp": "2026-03-20T07:20:00Z"},
                {"status": "In Transit", "note": "At Hyderabad sorting center.", "timestamp": "2026-03-25T13:15:00Z"},
            ],
        },
        "SE-3302": {
            "item": "USB-C Cable",
            "price": 299,
            "quantity": 2,
            "status": "Delivered",
            "delivered": "2 days ago",
            "customer": "Arjun",
            "ordered_at": "2026-03-15T08:10:00Z",
            "events": [
                {"status": "Order Placed", "note": "Order confirmed.", "timestamp": "2026-03-15T08:10:00Z"},
                {"status": "Delivered", "note": "Delivered at front desk.", "timestamp": "2026-03-24T16:45:00Z"},
            ],
        },
        "SE-5510": {
            "item": "Laptop Stand",
            "price": 1899,
            "quantity": 1,
            "status": "Processing",
            "ordered": "today",
            "estimated_delivery": "in 5 days",
            "customer": "Vishwa",
            "ordered_at": "2026-03-26T06:50:00Z",
            "events": [
                {"status": "Order Placed", "note": "Order created.", "timestamp": "2026-03-26T06:50:00Z"},
                {"status": "Processing", "note": "Warehouse picking in progress.", "timestamp": "2026-03-26T07:05:00Z"},
            ],
        },
    }


def _normalize_order_record(order: dict) -> dict:
    quantity = max(1, int(order.get("quantity", 1)))
    price = int(order.get("price", 0))
    subtotal = int(order.get("subtotal", price * quantity))
    return {
        "order_id": order.get("order_id", ""),
        "item": order.get("product_name", order.get("item", "")),
        "price": price,
        "quantity": quantity,
        "subtotal": subtotal,
        "status": order.get("status", "In Transit"),
        "customer": order.get("customer_name", order.get("customer", "Arjun")),
        "estimated_delivery": order.get("estimated_delivery", "5-7 business days"),
        "ordered_at": order.get("ordered_at", ""),
        "events": order.get("events", []),
    }


def _initial_order_events(status: str) -> list[dict]:
    return [
        {
            "status": "Order Placed",
            "note": "Order confirmed in ShopEasy system.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        {
            "status": status,
            "note": "Current latest order state.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ]


def _extract_customer_name_from_text(text: str) -> str | None:
    if not text:
        return None
    patterns = [
        r"(?:my name is|i am|this is)\s+([A-Za-z][A-Za-z\s]{1,30})",
        r"customer\s*[:=-]\s*([A-Za-z][A-Za-z\s]{1,30})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return None


def _normalize_agent_response(text: str) -> str:
    """Convert noisy markdown-heavy model output into clean readable plain text."""
    if not text:
        return ""

    raw_lines = str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned: list[str] = []

    for line in raw_lines:
        s = line.strip()
        if not s:
            cleaned.append("")
            continue

        s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
        s = re.sub(r"`([^`]*)`", r"\1", s)
        s = re.sub(r"^#{1,6}\s*", "", s)

        if re.fullmatch(r"[\-|:\s]{3,}", s):
            continue
        if re.fullmatch(r"(?:\d+\.|[-*])\s*[-]{2,}\s*", s):
            continue
        if s in {"|", "1. |", "- |"}:
            continue

        if s.startswith("|") and s.endswith("|"):
            cols = [c.strip() for c in s.strip("|").split("|")]
            cols = [c for c in cols if c]
            if not cols:
                continue
            if len(cols) >= 2:
                s = f"{cols[0]}: {'; '.join(cols[1:])}"
            else:
                s = cols[0]

        cleaned.append(s)

    normalized: list[str] = []
    prev_blank = False
    for line in cleaned:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        normalized.append(line)
        prev_blank = is_blank

    return "\n".join(normalized).strip()


async def _resolve_customer_for_session(session_id: str, explicit_customer: str | None = None) -> str | None:
    if explicit_customer and explicit_customer.strip():
        return explicit_customer.strip()
    profile = await redis_manager.get_profile(session_id)
    customer = (profile.get("customer_name") or "").strip()
    return customer or None


def _build_orders_summary(orders: list[dict], customer: str | None = None, session_id: str | None = None) -> dict:
    rows = orders
    if customer:
        customer_lower = customer.strip().lower()
        rows = [o for o in orders if str(o.get("customer", "")).strip().lower() == customer_lower]

    total_orders = len(rows)
    total_items = sum(int(o.get("quantity", 1)) for o in rows)
    total_spent = sum(int(o.get("subtotal", int(o.get("price", 0)) * int(o.get("quantity", 1)))) for o in rows)
    active_orders = [o for o in rows if str(o.get("status", "")).lower() not in {"delivered", "cancelled", "canceled"}]

    last_order = rows[-1] if rows else None
    return {
        "customer": customer or "all",
        "session_id": session_id,
        "total_orders": total_orders,
        "total_items": total_items,
        "total_spent": total_spent,
        "active_orders": len(active_orders),
        "last_order_id": (last_order or {}).get("order_id"),
        "last_order_eta": (last_order or {}).get("estimated_delivery"),
        "recent_orders": rows[-5:],
    }


async def _collect_orders(limit: int = 50) -> list[dict]:
    orders: list[dict] = []

    if db_manager.db is not None:
        cursor = db_manager.db.orders.find({}, {"_id": 0}).sort("order_id", 1).limit(max(1, min(limit, 200)))
        async for row in cursor:
            orders.append(_normalize_order_record(row))

    if not orders:
        for oid, row in in_memory_orders.items():
            row_with_id = dict(row)
            row_with_id.setdefault("order_id", oid)
            orders.append(_normalize_order_record(row_with_id))

    if not orders:
        for oid, row in _builtin_orders().items():
            row_with_id = dict(row)
            row_with_id.setdefault("order_id", oid)
            orders.append(_normalize_order_record(row_with_id))

    return orders[: max(1, min(limit, 200))]


async def _fast_voice_reply(user_text: str, session_id: str | None = None, order_id: str | None = None) -> str:
    """Low-latency path for voice mode using Groq-first model routing."""
    llm = get_llm(task="voice", temperature=0.1)
    context_task = asyncio.to_thread(retrieve_context, user_text, 4)

    resolved_order_id = str(order_id or "").strip().upper() or _extract_order_id_from_text(user_text)
    needs_summary = any(
        phrase in user_text.lower()
        for phrase in ["last order", "my orders", "how many orders", "what i ordered", "order summary", "eta"]
    )

    async def fetch_order_extra() -> str:
        if not resolved_order_id:
            return ""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=1.0) as client:
                res = await client.get(f"http://localhost:8000/api/mock/order/{resolved_order_id}")
                if res.status_code == 200:
                    return f"\nActive Order Context: {resolved_order_id}\nLive Order Data: {json.dumps(res.json(), ensure_ascii=True)}"
        except Exception:
            return ""
        return ""

    async def fetch_summary_extra() -> str:
        if not needs_summary:
            return ""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=1.1) as client:
                params = {"session_id": session_id} if session_id else None
                res = await client.get("http://localhost:8000/api/mock/orders/summary", params=params)
                if res.status_code == 200:
                    return f"\nLive Order Summary: {json.dumps(res.json(), ensure_ascii=True)}"
        except Exception:
            return ""
        return ""

    context, order_extra, summary_extra = await asyncio.gather(
        context_task,
        fetch_order_extra(),
        fetch_summary_extra(),
    )

    prompt = (
        "You are a fast voice customer support assistant for ShopEasy. "
        "Give a concise, grounded reply in 2-4 short sentences. "
        "Do not fabricate policy or order details. "
        f"\nUser: {user_text}\n"
        f"Knowledge: {context}{order_extra}{summary_extra}"
    )
    result = await llm.ainvoke(prompt)
    raw = (result.content or "").strip()
    return _normalize_agent_response(raw) or "I can help with that. Please share your order ID if you have one."


async def _early_voice_reply_preview(user_text: str) -> str:
    """Single-line early preview for partial transcript to improve perceived latency."""
    llm = get_llm(task="voice", temperature=0.0)
    prompt = (
        "You are a customer support assistant. "
        "Generate ONE short provisional reply based on partial user speech. "
        "Do not invent facts and mention that details are being checked if needed. "
        f"Partial user speech: {user_text}"
    )
    try:
        result = await asyncio.wait_for(llm.ainvoke(prompt), timeout=1.6)
        text = (result.content or "").strip()
        return _normalize_agent_response(text)[:220]
    except Exception:
        return "Working on your request, checking details now..."


class EmailInboundRequest(BaseModel):
    from_email: str
    subject: str = ""
    body: str
    session_id: str | None = None


async def _append_message(session_id: str, role: str, content: str):
    """Persist messages in MongoDB and mirror them into Redis session history."""
    await db_manager.append_message(session_id, role, content)
    await redis_manager.append_message(session_id, role, content)


async def _load_session_history(session_id: str):
    """Load chat history from Redis first, then fallback to MongoDB."""
    from langchain_core.messages import AIMessage, HumanMessage

    history_doc = await redis_manager.get_history(session_id)
    if not history_doc:
        history_doc = (await db_manager.get_session_history(session_id)).get("history", [])

    session_history = []
    for m in history_doc:
        if m.get("role") == "user":
            session_history.append(HumanMessage(content=m.get("content", "")))
        else:
            session_history.append(AIMessage(content=m.get("content", "")))

    return session_history


def _make_scoped_cache_key(user_text: str, order_id: str | None = None) -> str:
    scoped_text = f"[order:{order_id}] {user_text}" if order_id else user_text
    return make_cache_key(scoped_text)


async def _run_support_turn(session_id: str, user_text: str, session_history, order_id: str | None = None):
    """Run the LangGraph flow for one user turn and return a response with metadata."""
    from backend.agents.graph import app_graph

    customer_hint = _extract_customer_name_from_text(user_text)
    if customer_hint:
        await redis_manager.set_profile(session_id, {"customer_name": customer_hint})

    model_user_text = user_text
    if order_id and order_id not in user_text.upper():
        model_user_text = f"{user_text}\nMy active order ID is {order_id}."

    initial_state = {
        "session_id": session_id,
        "messages": session_history,
        "retry_count": 0,
    }
    if model_user_text != user_text:
        from langchain_core.messages import HumanMessage

        state_messages = list(session_history)
        if state_messages and isinstance(state_messages[-1], HumanMessage):
            state_messages[-1] = HumanMessage(content=model_user_text)
        else:
            state_messages.append(HumanMessage(content=model_user_text))
        initial_state["messages"] = state_messages

    final_state = await app_graph.ainvoke(initial_state)

    is_escalated = final_state.get("critic_decision") == "ESCALATE" or final_state.get("escalate", False)
    if is_escalated:
        response = "I cannot resolve this automatically. Human escalation triggered."
        try:
            bundle_obj = await generate_escalation_bundle(
                conversation_history=[m.content for m in session_history],
                user_query=user_text,
                intent=final_state.get("intent", "general"),
                priority=final_state.get("priority", "P3"),
                retrieved_context=final_state.get("retrieved_context", ""),
                critic_feedback=final_state.get("critic_feedback", ""),
            )
            bundle = json.dumps(bundle_obj.get("context_bundle", {}), ensure_ascii=True)
        except Exception as e:
            bundle = f"Local Ollama generation failed. Ensure Ollama is running with llama3.2:3b installed. Error: {str(e)}"

        await db_manager.log_session_activity(
            session_id,
            is_escalated=True,
            bundle=bundle,
            intent=final_state.get("intent", "general"),
            priority=final_state.get("priority", "P3"),
        )
    else:
        response = final_state.get("draft_response", "Sorry, I could not process that.")
        await db_manager.log_session_activity(
            session_id,
            intent=final_state.get("intent", "general"),
            priority=final_state.get("priority", "P3"),
        )

    response = _normalize_agent_response(response)

    await redis_manager.set_meta(
        session_id,
        intent=final_state.get("intent", "general"),
        priority=final_state.get("priority", "P3"),
        order_id=order_id,
    )

    return response, is_escalated, final_state


async def _process_voice_turn(session_id: str, audio_path: str, order_id: str | None = None):
    """Shared voice turn pipeline for both HTTP uploads and WS streaming turns."""
    global voice_pipeline

    transcribed_text, raw_stt = voice_pipeline.transcribe(audio_path)
    vad_result = voice_pipeline.run_vad(raw_stt)
    turn = voice_pipeline.detect_turn_end(transcribed_text, vad_result)

    if not vad_result.has_speech:
        return {
            "error": "No reliable speech detected. Please speak clearly and try again.",
            "pipeline": {
                "vad": {
                    "has_speech": vad_result.has_speech,
                    "speech_segments": vad_result.speech_segments,
                    "avg_no_speech_prob": round(vad_result.avg_no_speech_prob, 3),
                },
                "turn_detection": {
                    "is_end_of_turn": turn.is_end_of_turn,
                    "delay_ms": turn.delay_ms,
                    "reason": turn.reason,
                },
            },
        }

    if not turn.is_end_of_turn:
        return {
            "error": "Turn not complete yet. Please finish your sentence and retry.",
            "pipeline": {
                "vad": {
                    "has_speech": vad_result.has_speech,
                    "speech_segments": vad_result.speech_segments,
                    "avg_no_speech_prob": round(vad_result.avg_no_speech_prob, 3),
                },
                "turn_detection": {
                    "is_end_of_turn": turn.is_end_of_turn,
                    "delay_ms": turn.delay_ms,
                    "reason": turn.reason,
                },
            },
        }

    if not transcribed_text:
        return {"error": "Could not hear any speech. Please try again."}

    resolved_order_id = await _resolve_order_context(session_id, transcribed_text, explicit_order_id=order_id)
    model_user_text = transcribed_text
    if resolved_order_id and resolved_order_id not in transcribed_text.upper():
        model_user_text = f"{transcribed_text}\nMy active order ID is {resolved_order_id}."

    await _append_message(session_id, "user", model_user_text)

    cache_key = _make_scoped_cache_key(transcribed_text, resolved_order_id)
    cached = response_cache.get(cache_key)
    if cached:
        response_text = _normalize_agent_response(cached["response"])
        await _append_message(session_id, "ai", response_text)

        audio_filename = await voice_pipeline.synthesize(response_text, "backend/voice_output")
        return {
            "transcribed_text": transcribed_text,
            "response_text": response_text,
            "audio_url": f"/api/voice/audio/{audio_filename}",
            "pipeline": {
                "vad": {
                    "has_speech": vad_result.has_speech,
                    "speech_segments": vad_result.speech_segments,
                    "avg_no_speech_prob": round(vad_result.avg_no_speech_prob, 3),
                },
                "turn_detection": {
                    "is_end_of_turn": turn.is_end_of_turn,
                    "delay_ms": turn.delay_ms,
                    "reason": turn.reason,
                },
            },
        }

    if _as_bool("VOICE_FAST_MODE", "true"):
        response_text = await _fast_voice_reply(
            transcribed_text,
            session_id=session_id,
            order_id=resolved_order_id,
        )
        await db_manager.log_session_activity(session_id, intent="voice", priority="P3")
        await _append_message(session_id, "ai", response_text)
        response_cache.set(cache_key, response_text, metadata={"intent": "voice", "priority": "P3"})
    else:
        from langchain_core.messages import HumanMessage

        session_history = await _load_session_history(session_id)
        session_history.append(HumanMessage(content=model_user_text))

        response_text, is_escalated, final_state = await _run_support_turn(
            session_id,
            transcribed_text,
            session_history,
            order_id=resolved_order_id,
        )
        await _append_message(session_id, "ai", response_text)

        if not is_escalated and str(final_state.get("critic_decision", "APPROVE")).upper() == "APPROVE":
            response_cache.set(
                cache_key,
                response_text,
                metadata={
                    "intent": final_state.get("intent", "general"),
                    "priority": final_state.get("priority", "P4"),
                },
            )

    audio_filename = await voice_pipeline.synthesize(response_text, "backend/voice_output")

    return {
        "transcribed_text": transcribed_text,
        "response_text": response_text,
        "audio_url": f"/api/voice/audio/{audio_filename}",
        "pipeline": {
            "vad": {
                "has_speech": vad_result.has_speech,
                "speech_segments": vad_result.speech_segments,
                "avg_no_speech_prob": round(vad_result.avg_no_speech_prob, 3),
            },
            "turn_detection": {
                "is_end_of_turn": turn.is_end_of_turn,
                "delay_ms": turn.delay_ms,
                "reason": turn.reason,
            },
        },
    }

@app.get("/")
def health_check():
    return {"status": "ok", "message": "React Support Core Online"}

@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    return await db_manager.get_session_history(session_id)

@app.get("/api/admin/metrics")
async def get_metrics():
    return await db_manager.get_dashboard_metrics()


@app.get("/api/admin/queue")
async def get_live_queue():
    return await db_manager.get_live_queue()


@app.get("/api/admin/analytics")
async def get_analytics():
    return await db_manager.get_analytics_snapshot()


@app.post("/api/admin/kb/upload")
async def upload_kb_document(file: UploadFile = File(...), category: str = Form("general")):
    try:
        content = (await file.read()).decode("utf-8", errors="ignore")
        result = append_kb_text(content, category=category)
        response_cache.clear()
        return {
            "status": "ok",
            "filename": file.filename,
            "category": category,
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KB upload failed: {e}")

@app.get("/api/mock/order/{order_id}")
async def get_mock_order(order_id: str):
    normalized_order_id = order_id.upper()

    if normalized_order_id in in_memory_orders:
        row = dict(in_memory_orders[normalized_order_id])
        row.setdefault("order_id", normalized_order_id)
        row.setdefault("events", [])
        return row

    if db_manager.db is not None:
        order_doc = await db_manager.db.orders.find_one({"order_id": normalized_order_id}, {"_id": 0})
        if order_doc:
            quantity = max(1, int(order_doc.get("quantity", 1)))
            price = int(order_doc.get("price", 0))
            return {
                "item": order_doc.get("product_name"),
                "price": price,
                "quantity": quantity,
                "subtotal": int(order_doc.get("subtotal", price * quantity)),
                "status": order_doc.get("status", "In Transit"),
                "ordered": order_doc.get("ordered", "today"),
                "estimated_delivery": order_doc.get("estimated_delivery", "5-7 business days"),
                "customer": order_doc.get("customer_name", "Arjun"),
                "ordered_at": order_doc.get("ordered_at", ""),
                "order_id": normalized_order_id,
            }

    orders = _builtin_orders()
    if normalized_order_id in orders:
        row = dict(orders[normalized_order_id])
        row.setdefault("order_id", normalized_order_id)
        row.setdefault("events", [])
        row.setdefault("quantity", 1)
        row.setdefault("subtotal", int(row.get("price", 0)) * int(row.get("quantity", 1)))
        return row

    raise HTTPException(status_code=404, detail="Order not found")


@app.post("/api/mock/order")
async def create_mock_order(payload: MockOrderCreate):
    if not payload.order_id.upper().startswith("SE-"):
        raise HTTPException(status_code=400, detail="order_id must follow SE-XXXX format")

    if db_manager.db is None:
        quantity = max(1, payload.quantity)
        subtotal = payload.price * quantity
        events = _initial_order_events(payload.status)
        in_memory_orders[payload.order_id.upper()] = {
            "item": payload.product_name,
            "price": payload.price,
            "quantity": quantity,
            "subtotal": subtotal,
            "status": payload.status,
            "ordered": "today",
            "estimated_delivery": f"{payload.eta_days} days",
            "customer": payload.customer_name,
            "ordered_at": datetime.now(timezone.utc).isoformat(),
            "events": events,
            "order_id": payload.order_id.upper(),
        }
        if payload.session_id:
            await redis_manager.set_profile(payload.session_id, {"customer_name": payload.customer_name})
        return {
            "success": True,
            "order_id": payload.order_id.upper(),
            "estimated_delivery": f"{payload.eta_days} days",
        }

    quantity = max(1, payload.quantity)
    subtotal = payload.price * quantity
    order_doc = {
        "order_id": payload.order_id.upper(),
        "product_name": payload.product_name,
        "price": payload.price,
        "quantity": quantity,
        "subtotal": subtotal,
        "customer_name": payload.customer_name,
        "status": payload.status,
        "estimated_delivery": f"{payload.eta_days} days",
        "ordered": "today",
        "ordered_at": datetime.now(timezone.utc).isoformat(),
        "events": _initial_order_events(payload.status),
    }

    await db_manager.db.orders.update_one(
        {"order_id": order_doc["order_id"]},
        {"$set": order_doc},
        upsert=True,
    )

    if payload.session_id:
        await redis_manager.set_profile(payload.session_id, {"customer_name": payload.customer_name})

    return {
        "success": True,
        "order_id": order_doc["order_id"],
        "estimated_delivery": f"{payload.eta_days} days",
    }


@app.get("/api/mock/orders")
async def list_mock_orders(limit: int = 50):
    rows = await _collect_orders(limit=limit)
    return {"orders": rows, "count": len(rows)}


@app.get("/api/mock/orders/summary")
async def orders_summary(customer: str | None = None, session_id: str | None = None):
    rows = await _collect_orders(limit=200)
    resolved_customer = customer
    if not resolved_customer and session_id:
        resolved_customer = await _resolve_customer_for_session(session_id)
    return _build_orders_summary(rows, customer=resolved_customer, session_id=session_id)


@app.post("/api/session/profile/{session_id}")
async def upsert_session_profile(session_id: str, payload: SessionProfileUpdate):
    profile = {
        "customer_name": payload.customer_name,
        "email": payload.email,
        "phone": payload.phone,
    }
    await redis_manager.set_profile(session_id, profile)
    return {"ok": True, "session_id": session_id, "profile": await redis_manager.get_profile(session_id)}


@app.get("/api/session/profile/{session_id}")
async def get_session_profile(session_id: str):
    profile = await redis_manager.get_profile(session_id)
    return {"session_id": session_id, "profile": profile}


@app.get("/api/mock/order/{order_id}/events")
async def get_order_events(order_id: str):
    normalized_order_id = order_id.upper()
    if db_manager.db is not None:
        row = await db_manager.db.orders.find_one(
            {"order_id": normalized_order_id},
            {"_id": 0, "order_id": 1, "events": 1},
        )
        if row is not None:
            return {"order_id": normalized_order_id, "events": row.get("events") or []}

    if normalized_order_id in in_memory_orders:
        return {"order_id": normalized_order_id, "events": in_memory_orders[normalized_order_id].get("events", [])}

    builtin = _builtin_orders().get(normalized_order_id)
    if builtin:
        return {"order_id": normalized_order_id, "events": builtin.get("events", [])}

    raise HTTPException(status_code=404, detail="Order not found")


@app.post("/api/mock/order/{order_id}/event")
async def add_order_event(order_id: str, payload: OrderEventCreate):
    normalized_order_id = order_id.upper()
    event = {
        "status": payload.status,
        "note": payload.note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if db_manager.db is not None:
        await db_manager.db.orders.update_one(
            {"order_id": normalized_order_id},
            {
                "$set": {"status": payload.status},
                "$push": {"events": event},
            },
            upsert=True,
        )
        return {"ok": True, "order_id": normalized_order_id, "event": event}

    if normalized_order_id in in_memory_orders:
        in_memory_orders[normalized_order_id].setdefault("events", _initial_order_events("In Transit"))
        in_memory_orders[normalized_order_id]["status"] = payload.status
        in_memory_orders[normalized_order_id]["events"].append(event)
        return {"ok": True, "order_id": normalized_order_id, "event": event}

    builtin = _builtin_orders().get(normalized_order_id)
    if builtin:
        in_memory_orders[normalized_order_id] = {
            **builtin,
            "order_id": normalized_order_id,
            "status": payload.status,
        }
        in_memory_orders[normalized_order_id].setdefault("events", _initial_order_events(payload.status))
        in_memory_orders[normalized_order_id]["events"].append(event)
        return {"ok": True, "order_id": normalized_order_id, "event": event}

    raise HTTPException(status_code=404, detail="Order not found")

@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        from langchain_core.messages import AIMessage, HumanMessage

        session_history = await _load_session_history(session_id)
        
        while True:
            raw_data = await websocket.receive_text()
            data = raw_data
            explicit_order_id = ""

            try:
                payload = json.loads(raw_data)
                if isinstance(payload, dict):
                    data = str(payload.get("text") or payload.get("message") or "").strip()
                    explicit_order_id = str(payload.get("order_id") or "").strip().upper()
            except Exception:
                data = raw_data

            if not data.strip():
                continue

            resolved_order_id = await _resolve_order_context(
                session_id,
                user_text=data,
                explicit_order_id=explicit_order_id,
            )
            model_user_text = data
            if resolved_order_id and resolved_order_id not in data.upper():
                model_user_text = f"{data}\nMy active order ID is {resolved_order_id}."

            print(f"[{session_id}] User: {data}")
            
            # Save User Message to MongoDB
            await _append_message(session_id, "user", model_user_text)
            session_history.append(HumanMessage(content=model_user_text))

            # Cache fast-path for repeated queries.
            cache_key = _make_scoped_cache_key(data, resolved_order_id)
            cached = response_cache.get(cache_key)
            if cached:
                response = _normalize_agent_response(cached["response"])
                cached_meta = cached.get("metadata", {})
                await _append_message(session_id, "ai", response)
                await db_manager.log_session_activity(
                    session_id,
                    intent=cached_meta.get("intent", "general"),
                    priority=cached_meta.get("priority", "P4"),
                )
                await redis_manager.set_meta(
                    session_id,
                    intent=cached_meta.get("intent", "general"),
                    priority=cached_meta.get("priority", "P4"),
                    order_id=resolved_order_id,
                )
                session_history.append(AIMessage(content=response))
                await manager.send_personal_message(response, session_id)
                continue
            
            try:
                response, is_escalated, final_state = await _run_support_turn(
                    session_id,
                    data,
                    session_history,
                    order_id=resolved_order_id,
                )
                session_history.append(AIMessage(content=response))

                await _append_message(session_id, "ai", response)
                await manager.send_personal_message(response, session_id)

                if not is_escalated and str(final_state.get("critic_decision", "APPROVE")).upper() == "APPROVE":
                    response_cache.set(
                        cache_key,
                        response,
                        metadata={
                            "intent": final_state.get("intent", "general"),
                            "priority": final_state.get("priority", "P4"),
                        },
                    )
                
            except Exception as e:
                print(f"Graph execution error: {e}")
                await manager.send_personal_message("Temporary system error. Please try again.", session_id)
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"[{session_id}] Disconnected")

@app.post("/api/voice/transcribe")
async def process_voice(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    order_id: str | None = Form(None),
):
    global whisper_model
    global voice_pipeline
    if whisper_model is None:
        print("\n[VOICE] Whisper fallback loading...")
        import whisper
        whisper_model = whisper.load_model("base")
    if voice_pipeline is None:
        voice_pipeline = VoicePipeline(whisper_model)
        
    os.makedirs("backend/voice_output", exist_ok=True)
    temp_audio_path = f"backend/voice_output/temp_{session_id}.webm"
    with open(temp_audio_path, "wb") as f:
        f.write(await audio.read())
    print(f"\n[VOICE] Processing uploaded voice turn for session {session_id}...")
    return await _process_voice_turn(session_id, temp_audio_path, order_id=order_id)


@app.post("/api/email/inbound")
async def process_inbound_email(payload: EmailInboundRequest):
    """Receives inbound email content and routes it through the same support flow."""
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Email body is required")

    session_id = payload.session_id or f"email-{uuid.uuid4().hex[:10]}"
    await redis_manager.set_profile(session_id, {"email": payload.from_email})
    email_text = (
        f"[Email from {payload.from_email}]\n"
        f"Subject: {payload.subject.strip() or '(no subject)'}\n"
        f"Message: {payload.body.strip()}"
    )

    cache_key = make_cache_key(email_text)
    cached = response_cache.get(cache_key)
    if cached:
        response = _normalize_agent_response(cached["response"])
        smtp_sent, smtp_error = await send_smtp_email(
            payload.from_email,
            f"Re: {payload.subject.strip() or 'ShopEasy Support'}",
            response,
        )
        await _append_message(session_id, "user", email_text)
        await _append_message(session_id, "ai", response)
        await db_manager.log_session_activity(session_id, intent="email", priority="P3")
        await redis_manager.enqueue_email_ticket(
            {
                "session_id": session_id,
                "channel": "email",
                "from_email": payload.from_email,
                "subject": payload.subject,
                "request": payload.body,
                "response": response,
                "cached": True,
                "smtp_sent": smtp_sent,
                "smtp_error": smtp_error,
            }
        )
        return {
            "session_id": session_id,
            "channel": "email",
            "reply": response,
            "cached": True,
            "smtp_sent": smtp_sent,
            "smtp_error": smtp_error,
        }

    from langchain_core.messages import HumanMessage

    session_history = await _load_session_history(session_id)
    await _append_message(session_id, "user", email_text)
    session_history.append(HumanMessage(content=email_text))

    response, is_escalated, final_state = await _run_support_turn(session_id, email_text, session_history)
    response = _normalize_agent_response(response)
    await _append_message(session_id, "ai", response)

    smtp_sent, smtp_error = await send_smtp_email(
        payload.from_email,
        f"Re: {payload.subject.strip() or 'ShopEasy Support'}",
        response,
    )

    if not is_escalated and str(final_state.get("critic_decision", "APPROVE")).upper() == "APPROVE":
        response_cache.set(
            cache_key,
            response,
            metadata={
                "intent": final_state.get("intent", "email"),
                "priority": final_state.get("priority", "P3"),
            },
        )

    await redis_manager.enqueue_email_ticket(
        {
            "session_id": session_id,
            "channel": "email",
            "from_email": payload.from_email,
            "subject": payload.subject,
            "request": payload.body,
            "response": response,
            "escalated": is_escalated,
            "intent": final_state.get("intent", "email"),
            "priority": final_state.get("priority", "P3"),
            "smtp_sent": smtp_sent,
            "smtp_error": smtp_error,
        }
    )

    return {
        "session_id": session_id,
        "channel": "email",
        "reply": response,
        "escalated": is_escalated,
        "smtp_sent": smtp_sent,
        "smtp_error": smtp_error,
    }


@app.websocket("/ws/voice-stream/{session_id}")
async def websocket_voice_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    chunk_path = None
    buffer = bytearray()
    turn_active = False
    processing = False
    last_chunk_ts = 0.0
    turn_lock = asyncio.Lock()
    silence_timeout_sec = float(os.getenv("VOICE_STREAM_SILENCE_SEC", "1.1"))
    min_turn_bytes = int(os.getenv("VOICE_STREAM_MIN_BYTES", "3500"))
    partial_enabled = _as_bool("VOICE_STREAM_PARTIAL_ENABLED", "true")
    partial_interval_sec = float(os.getenv("VOICE_STREAM_PARTIAL_INTERVAL_SEC", "0.85"))
    partial_min_bytes = int(os.getenv("VOICE_STREAM_PARTIAL_MIN_BYTES", "9000"))

    partial_last_text = ""
    partial_last_infer_ts = 0.0
    early_reply_sent = False
    partial_task: asyncio.Task | None = None
    active_order_id = ""

    async def finalize_turn(trigger: str):
        nonlocal chunk_path, buffer, turn_active, processing
        async with turn_lock:
            if processing or not turn_active:
                return
            if len(buffer) < min_turn_bytes:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "turn_error",
                            "error": "No clear speech detected.",
                            "bytes": len(buffer),
                            "trigger": trigger,
                        }
                    )
                )
                buffer = bytearray()
                chunk_path = None
                turn_active = False
                return

            processing = True
            if chunk_path is None:
                os.makedirs("backend/voice_output", exist_ok=True)
                chunk_path = Path(f"backend/voice_output/stream_{session_id}_{uuid.uuid4().hex}.webm")
            chunk_path.write_bytes(buffer)

        await websocket.send_text(json.dumps({"type": "processing", "bytes": len(buffer), "trigger": trigger}))
        result = await _process_voice_turn(session_id, str(chunk_path), order_id=active_order_id)
        await websocket.send_text(json.dumps({"type": "turn_result", "payload": result, "trigger": trigger}))

        async with turn_lock:
            buffer = bytearray()
            chunk_path = None
            turn_active = False
            processing = False

    async def silence_watchdog():
        nonlocal last_chunk_ts
        loop = asyncio.get_running_loop()
        while True:
            await asyncio.sleep(0.12)
            if not turn_active or processing:
                continue
            if not buffer or last_chunk_ts <= 0:
                continue
            if (loop.time() - last_chunk_ts) >= silence_timeout_sec:
                await finalize_turn("auto-silence")

    async def partial_preview_loop():
        nonlocal partial_last_text, partial_last_infer_ts, early_reply_sent
        loop = asyncio.get_running_loop()
        while True:
            await asyncio.sleep(0.14)
            if not partial_enabled or not turn_active or processing:
                continue
            if len(buffer) < partial_min_bytes:
                continue
            now_ts = loop.time()
            if now_ts - partial_last_infer_ts < partial_interval_sec:
                continue
            partial_last_infer_ts = now_ts

            try:
                os.makedirs("backend/voice_output", exist_ok=True)
                sample_path = Path(f"backend/voice_output/partial_{session_id}_{uuid.uuid4().hex}.webm")
                sample_path.write_bytes(bytes(buffer))
                text, _raw = await asyncio.to_thread(voice_pipeline.transcribe, str(sample_path))
                try:
                    sample_path.unlink(missing_ok=True)
                except Exception:
                    pass

                cleaned = (text or "").strip()
                if not cleaned:
                    continue
                if cleaned == partial_last_text:
                    continue
                partial_last_text = cleaned
                await websocket.send_text(json.dumps({"type": "partial_transcript", "text": cleaned}))

                if not early_reply_sent and len(cleaned.split()) >= 6:
                    early_text = await _early_voice_reply_preview(cleaned)
                    await websocket.send_text(json.dumps({"type": "early_reply", "text": early_text}))
                    early_reply_sent = True
            except Exception:
                continue

    try:
        watchdog_task = asyncio.create_task(silence_watchdog())
        partial_task = asyncio.create_task(partial_preview_loop())
        await websocket.send_text(json.dumps({"type": "ready", "session_id": session_id}))
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            if message.get("bytes") is not None:
                if chunk_path is None:
                    os.makedirs("backend/voice_output", exist_ok=True)
                    chunk_path = Path(f"backend/voice_output/stream_{session_id}_{uuid.uuid4().hex}.webm")
                buffer.extend(message["bytes"])
                last_chunk_ts = asyncio.get_running_loop().time()
                if len(buffer) > 0 and len(buffer) % (64 * 1024) < 2048:
                    await websocket.send_text(json.dumps({"type": "chunk", "bytes": len(buffer)}))
                continue

            if message.get("text") is None:
                continue

            try:
                payload = json.loads(message["text"])
            except Exception:
                payload = {"type": message["text"]}

            msg_type = payload.get("type")
            if msg_type == "start_turn":
                active_order_id = await _resolve_order_context(
                    session_id,
                    explicit_order_id=payload.get("order_id"),
                )
                buffer = bytearray()
                chunk_path = None
                turn_active = True
                processing = False
                last_chunk_ts = asyncio.get_running_loop().time()
                partial_last_text = ""
                partial_last_infer_ts = 0.0
                early_reply_sent = False
                await websocket.send_text(
                    json.dumps({"type": "turn_started", "order_id": active_order_id or None})
                )
            elif msg_type == "end_turn":
                if payload.get("order_id"):
                    active_order_id = await _resolve_order_context(
                        session_id,
                        explicit_order_id=payload.get("order_id"),
                    )
                await finalize_turn("client-end")
            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        try:
            watchdog_task.cancel()
            await watchdog_task
        except BaseException:
            pass
        if partial_task is not None:
            try:
                partial_task.cancel()
                await partial_task
            except BaseException:
                pass

@app.get("/api/voice/audio/{filename}")
async def get_audio(filename: str):
    file_path = f"backend/voice_output/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    return {"error": "Audio not found"}
