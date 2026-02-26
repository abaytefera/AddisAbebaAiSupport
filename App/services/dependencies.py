from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from App.services.jwt_handler import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        print(token)
        print("result")
        # Check if payload is None or empty
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Could not validate credentials"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token"
        )

def require_system_admin(user=Depends(get_current_user)):
    # Defensive check: ensure user is a dictionary and has the key
    if not user or user.get("role") != "SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access denied: System Admin required"
        )
    return user

def require_company_admin(user=Depends(get_current_user)):
    # Defensive check: ensure user is a dictionary and has the key
    if not user or user.get("role") != "COMPANY_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access denied: Company Admin required"
        )
    return user