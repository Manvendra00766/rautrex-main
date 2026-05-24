import os
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Any
from dotenv import load_dotenv
from core.config import settings
from core.logger import logger

load_dotenv()

from supabase_client import supabase

async def sign_up(email, password, full_name):
    return supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"full_name": full_name}}
    })

async def sign_in(email, password):
    return supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })

async def sign_out():
    return supabase.auth.sign_out()

async def refresh_session(refresh_token: str):
    return supabase.auth.refresh_session(refresh_token)

security = HTTPBearer()

class User(BaseModel):
    id: str
    email: str
    db: Any = None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    
    # METHOD 1: Use Supabase API to verify token (Most Reliable)
    # This avoids issues with local JWT secrets, algorithms, and clock skew.
    try:
        # Note: get_user() will validate the token against Supabase Auth
        response = supabase.auth.get_user(token)
        
        if response and response.user:
            from supabase import create_client
            from supabase_client import SUPABASE_URL, SUPABASE_ANON_KEY
            user_client = None
            if SUPABASE_URL and SUPABASE_ANON_KEY:
                try:
                    user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                    user_client.postgrest.auth(token)
                except Exception as e_client:
                    logger.error(f"Failed to create scoped Supabase client: {str(e_client)}")
            
            return User(
                id=response.user.id,
                email=response.user.email or "",
                db=user_client
            )
            
        logger.error("Supabase Auth: get_user returned no user")
    except Exception as e:
        logger.warning(f"Supabase API auth failed: {str(e)}. Falling back to local decode.")

    # METHOD 2: Fallback to local JWT decode if API fails or for performance
    try:
        # Get secret directly from env to ensure it's fresh after load_dotenv()
        secret = os.getenv("SUPABASE_JWT_SECRET") or settings.SECRET_KEY
        algo = os.getenv("ALGORITHM") or "HS256"
        
        payload = jwt.decode(
            token, 
            secret, 
            algorithms=[algo], 
            options={"verify_aud": False}
        )
        
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        
        if user_id:
            from supabase import create_client
            from supabase_client import SUPABASE_URL, SUPABASE_ANON_KEY
            user_client = None
            if SUPABASE_URL and SUPABASE_ANON_KEY:
                try:
                    user_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                    user_client.postgrest.auth(token)
                except Exception as e_client:
                    logger.error(f"Failed to create scoped Supabase client: {str(e_client)}")
            return User(id=user_id, email=email or "", db=user_client)
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing sub",
        )
        
    except JWTError as e:
        logger.error(f"JWT Verification Failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Unexpected Auth Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
