from supabase_client import supabase

async def create_notification(user_id: str, type: str, title: str, body: str, metadata: dict = {}):
    valid_types = ["signal", "price_alert", "backtest_complete", "portfolio", "system"]
    if type not in valid_types:
        raise ValueError(f"Invalid notification type: {type}")
        
    result = supabase.table("notifications").insert({
        "user_id": user_id,
        "type": type,
        "title": title,
        "body": body,
        "metadata": metadata,
        "is_read": False
    }).execute()
    return result.data[0] if result.data else None

async def get_notifications(user_id: str, limit: int = 50, offset: int = 0):
    # unread-first order
    return supabase.table("notifications") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("is_read", desc=False) \
        .order("created_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()

async def get_unread_count(user_id: str) -> int:
    result = supabase.table("notifications") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .eq("is_read", False) \
        .execute()
    return result.count or 0

async def mark_read(user_id: str, notification_id: str):
    return supabase.table("notifications") \
        .update({"is_read": True}) \
        .eq("id", notification_id) \
        .eq("user_id", user_id) \
        .execute()

async def mark_all_read(user_id: str):
    return supabase.table("notifications") \
        .update({"is_read": True}) \
        .eq("user_id", user_id) \
        .eq("is_read", False) \
        .execute()
