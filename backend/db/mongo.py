import os
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient


class MongoDBManager:
    client: AsyncIOMotorClient = None
    db = None

    async def connect_to_mongo(self):
        # Default fallback to local IPv4 to avoid Windows localhost binding issues
        mongo_uri = os.getenv("MONGO_URI") or "mongodb://127.0.0.1:27017"
        try:
            print(f"Connecting to MongoDB at {mongo_uri}...")
            self.client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=2000)
            self.db = self.client.ai_customer_support
            # Test connection
            await self.client.server_info()
            print("Successfully connected to MongoDB.")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")

    async def close_mongo_connection(self):
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")

    async def log_session_activity(
        self,
        session_id: str,
        is_escalated: bool = False,
        bundle: str = None,
        intent: str = None,
        priority: str = None,
    ):
        """Creates or updates a session log."""
        if self.db is None: return
        try:
            collection = self.db.support_sessions
            
            update_data = {"last_active": datetime.now(timezone.utc)}
            if is_escalated:
                update_data["is_escalated"] = True
                update_data["escalation_bundle"] = bundle
            if intent:
                update_data["intent"] = intent
            if priority:
                update_data["priority"] = priority
                
            await collection.update_one(
                {"session_id": session_id},
                {"$set": update_data, "$setOnInsert": {"created_at": datetime.now(timezone.utc), "history": []}},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB log error: {e}")

    async def append_message(self, session_id: str, role: str, content: str):
        """Saves a message to the permanent history array."""
        if self.db is None: return
        try:
            collection = self.db.support_sessions
            msg = {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc)
            }
            await collection.update_one(
                {"session_id": session_id},
                {"$push": {"history": msg}},
                upsert=True
            )
        except Exception as e:
            print(f"MongoDB append error: {e}")
        
    async def get_dashboard_metrics(self):
        """Aggregates dashboard metrics from MongoDB."""
        if self.db is None:
            return {"active_sessions": 0, "total_messages": 0, "escalations_count": 0, "recent_activity": []}
            
        collection = self.db.support_sessions
        now = datetime.now(timezone.utc)
        active_since = now - timedelta(minutes=30)

        active_sessions = await collection.count_documents({"last_active": {"$gte": active_since}})
        escalated_sessions = await collection.count_documents({"is_escalated": True})

        # Aggregate real message counts from history arrays
        message_agg = await collection.aggregate([
            {"$project": {"count": {"$size": {"$ifNull": ["$history", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$count"}}},
        ]).to_list(length=1)
        total_messages = message_agg[0]["total"] if message_agg else 0

        recent_cursor = collection.find({"is_escalated": True}).sort("last_active", -1).limit(10)
        recent_activity = []
        async for doc in recent_cursor:
            recent_activity.append({
                "session_id": doc.get("session_id"),
                "bundle": doc.get("escalation_bundle", "No bundle generated."),
                "priority": doc.get("priority", "P3"),
                "timestamp": doc.get("last_active").strftime("%H:%M:%S") if doc.get("last_active") else "Just now"
            })
            
        return {
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "escalations_count": escalated_sessions,
            "recent_activity": recent_activity
        }

    async def get_live_queue(self):
        """Returns escalated sessions for live agent queue view."""
        if self.db is None:
            return []

        collection = self.db.support_sessions
        cursor = collection.find({"is_escalated": True}).sort("last_active", -1).limit(25)
        queue = []
        async for doc in cursor:
            queue.append({
                "session_id": doc.get("session_id"),
                "priority": doc.get("priority", "P3"),
                "intent": doc.get("intent", "general"),
                "last_active": doc.get("last_active").strftime("%Y-%m-%d %H:%M:%S") if doc.get("last_active") else "-",
                "bundle": doc.get("escalation_bundle", "No bundle generated."),
            })
        return queue

    async def get_analytics_snapshot(self):
        """Returns aggregate analytics for admin charts/cards."""
        if self.db is None:
            return {
                "intent_breakdown": {},
                "priority_breakdown": {},
                "escalation_rate": 0.0,
                "total_sessions": 0,
            }

        collection = self.db.support_sessions
        total_sessions = await collection.count_documents({})
        escalated_sessions = await collection.count_documents({"is_escalated": True})

        intent_rows = await collection.aggregate([
            {"$group": {"_id": {"$ifNull": ["$intent", "unknown"]}, "count": {"$sum": 1}}}
        ]).to_list(length=20)
        priority_rows = await collection.aggregate([
            {"$group": {"_id": {"$ifNull": ["$priority", "P3"]}, "count": {"$sum": 1}}}
        ]).to_list(length=10)

        intent_breakdown = {row["_id"]: row["count"] for row in intent_rows}
        priority_breakdown = {row["_id"]: row["count"] for row in priority_rows}
        escalation_rate = (escalated_sessions / total_sessions * 100.0) if total_sessions else 0.0

        return {
            "intent_breakdown": intent_breakdown,
            "priority_breakdown": priority_breakdown,
            "escalation_rate": round(escalation_rate, 2),
            "total_sessions": total_sessions,
        }
        
    async def get_session_history(self, session_id: str):
        """Fetches the permanent chat history for a session."""
        if self.db is None: return {"history": []}
        collection = self.db.support_sessions
        doc = await collection.find_one({"session_id": session_id}, {"_id": 0, "history": 1})
        return doc if doc else {"history": []}

db_manager = MongoDBManager()
