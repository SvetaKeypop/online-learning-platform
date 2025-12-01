from sqlalchemy.orm import Session
from .models import UserORM
from ..domain.entities import User
from ..application.use_cases.register_user import IUserRepository

def to_domain(u: UserORM) -> User:
    return User(id=u.id, email=u.email, role=u.role)

class UserRepository(IUserRepository):
    def __init__(self, db: Session): self.db = db

    def get_by_email(self, email: str) -> User | None:
        row = self.db.query(UserORM).filter(UserORM.email == email).first()
        return to_domain(row) if row else None

    def create(self, email: str, password_hash: str, role: str = "student") -> User:
        row = UserORM(email=email, password_hash=password_hash, role=role)
        self.db.add(row); self.db.commit(); self.db.refresh(row)
        return to_domain(row)
