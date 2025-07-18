from typing import Union, Any
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jose
from ..settings import firestore_db
from .utils import ALGORITHM, JWT_SECRET_KEY

from jose import jwt
from pydantic import ValidationError

reuseable_oauth = OAuth2PasswordBearer(tokenUrl="api/v1/login", scheme_name="JWT")
reuseable_oauth_optional = OAuth2PasswordBearer(tokenUrl="api/v1/login", scheme_name="JWT", auto_error=False)

async def get_current_user(token: str = Depends(reuseable_oauth)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload["sub"]
    except jose.exceptions.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_optional(token: str = Depends(reuseable_oauth_optional)) -> Union[str, None]:
    """Get the current user from the token, if it exists. else return None"""
    if not token:
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        if datetime.fromtimestamp(payload["exp"]) < datetime.now():
            return None
        return payload["sub"]
    except jose.exceptions.ExpiredSignatureError:
        return None
    except (jwt.JWTError, ValidationError):
        return None