import asyncio
from fastapi import HTTPException, Header
from supabase_client import supabase, SUPABASE_URL, SUPABASE_ANON_KEY
from supabase import create_client
from cachetools import TTLCache

# Cache verified users for 5 minutes to avoid Supabase API thrashing
token_cache = TTLCache(maxsize=1000, ttl=300)

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "").strip()
    
    if token in token_cache:
        return token_cache[token]
    
    try:
        # Prevent blocking the FastAPI event loop during synchronous HTTP requests
        response = await asyncio.to_thread(supabase.auth.get_user, token)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Create a scoped client for RLS
        user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_client.postgrest.auth(token)
        
        # Attach the scoped client to the user object for easy access
        user = response.user
        user.db = user_client
        
        # Cache the resulting user object
        token_cache[token] = user
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
