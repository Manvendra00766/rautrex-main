from fastapi import Depends, HTTPException, Header
from supabase_client import supabase, SUPABASE_URL, SUPABASE_ANON_KEY
from supabase import create_client

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "").strip()
    
    try:
        response = supabase.auth.get_user(token)
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Create a scoped client for RLS
        user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        user_client.postgrest.auth(token)
        
        # Attach the scoped client to the user object for easy access
        user = response.user
        user.db = user_client
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")
