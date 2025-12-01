from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from ..config import settings

pwd = CryptContext(
    schemes=["bcrypt_sha256"],
    deprecated="auto",
    bcrypt_sha256__truncate_error=False,
)

class PasswordHasher:
    def hash(self, plain: str) -> str: return pwd.hash(plain)
    def verify(self, plain: str, hashed: str) -> bool: return pwd.verify(plain, hashed)

def create_access_token(sub: str, role: str = "student", minutes: int = 60) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": sub, "role": role, "exp": exp}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    """Возвращает email (sub) из токена или кидает JWTError."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    sub = payload.get("sub")
    if not sub:
        raise JWTError("No subject")
    return sub
