from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from sqlalchemy.orm import Session

from ....infrastructure.db import get_db
from ....infrastructure.repositories import UserRepository
from ....infrastructure.security import PasswordHasher, create_access_token, decode_token
from ....application.use_cases.register_user import RegisterUser
from ....interfaces.http.schemas import RegisterReq, LoginReq, UserResp, TokenResp
from ....infrastructure.models import UserORM
from ....config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer()

def get_limiter(request: Request) -> Limiter:
    return request.app.state.limiter

@router.get("/health")
def health():
    return {"status": "ok"}

def _register_impl(
    request: Request,
    payload: RegisterReq,
    db: Session,
):
    uc = RegisterUser(repo=UserRepository(db), hasher=PasswordHasher())
    try:
        user = uc.execute(payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResp(id=user.id, email=user.email, role=user.role)

@router.post("/register", response_model=UserResp, status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    payload: RegisterReq,
    db: Session = Depends(get_db),
    limiter: Limiter = Depends(get_limiter)
):
    # Применяем rate limiting через декоратор
    limited_func = limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")(_register_impl)
    return limited_func(request, payload, db)

def _login_impl(
    request: Request,
    payload: LoginReq,
    db: Session,
):
    row = db.query(UserORM).filter(UserORM.email == payload.email).first()
    if not row or not PasswordHasher().verify(payload.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # добавим роль в токен
    token = create_access_token(sub=row.email, role=row.role)
    return TokenResp(access_token=token)

@router.post("/login", response_model=TokenResp)
def login(
    request: Request,
    payload: LoginReq,
    db: Session = Depends(get_db),
    limiter: Limiter = Depends(get_limiter)
):
    # Более строгий лимит для логина (защита от брутфорса)
    limited_func = limiter.limit("10/minute")(_login_impl)
    return limited_func(request, payload, db)


@router.get("/me", response_model=UserResp)
def me(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    # достаём email из токена
    try:
        email = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    row = db.query(UserORM).filter(UserORM.email == email).first()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return UserResp(id=row.id, email=row.email, role=row.role)
