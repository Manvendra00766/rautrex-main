import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from dotenv import load_dotenv

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

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


security = HTTPBearer()

class User(BaseModel):
    id: str
    email: str

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, 
            SUPABASE_JWT_SECRET, 
            algorithms=["HS256"], 
            options={"verify_aud": False}
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None:
            print("Auth Error: Missing sub in payload")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing sub",
            )
        return User(id=user_id, email=email)
    except jwt.ExpiredSignatureError:
        print("Auth Error: Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError as e:
        print(f"Auth Error: Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except Exception as e:
        print(f"Auth Error: Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )
