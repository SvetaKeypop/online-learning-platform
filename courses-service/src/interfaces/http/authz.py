from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from ...config import settings

bearer = HTTPBearer()

def get_claims(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        payload = jwt.decode(creds.credentials, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_admin(claims: dict = Depends(get_claims)) -> dict:
    # у нас в auth в токене sub=email. Роль узнаем из БД прогресса/курсов? Упростим:
    # добавим в дальнейшем "role" в токен при логине админа.
    role = claims.get("role", "student")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return claims

def get_user_email(claims: dict = Depends(get_claims)) -> str:
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return sub
