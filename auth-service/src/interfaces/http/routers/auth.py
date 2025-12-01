from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ....infrastructure.db import get_db
from ....infrastructure.repositories import UserRepository
from ....infrastructure.security import PasswordHasher, create_access_token, decode_token
from ....application.use_cases.register_user import RegisterUser
from ....interfaces.http.schemas import RegisterReq, LoginReq, UserResp, TokenResp
from ....infrastructure.models import UserORM

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/register", response_model=UserResp, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterReq, db: Session = Depends(get_db)):
    uc = RegisterUser(repo=UserRepository(db), hasher=PasswordHasher())
    try:
        user = uc.execute(payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UserResp(id=user.id, email=user.email, role=user.role)

@router.post("/login", response_model=TokenResp)
def login(payload: LoginReq, db: Session = Depends(get_db)):
    row = db.query(UserORM).filter(UserORM.email == payload.email).first()
    if not row or not PasswordHasher().verify(payload.password, row.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # добавим роль в токен
    token = create_access_token(sub=row.email, role=row.role)
    return TokenResp(access_token=token)


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
