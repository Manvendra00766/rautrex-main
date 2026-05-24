from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import settings
from core.exceptions import AuthenticationError
from core.logger import logger

security_scheme = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    return create_access_token(data, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credentials.credentials
    payload = verify_token(token)
    user_id: str = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Could not validate credentials")
    
    # Normally you would fetch user from DB here to ensure they exist and are active
    return {"user_id": user_id, "roles": payload.get("roles", ["user"])}

def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_roles = current_user.get("roles", [])
        if not any(role in allowed_roles for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker
