from ...domain.entities import User

class IUserRepository:
    def get_by_email(self, email: str) -> User | None: ...
    def create(self, email: str, password_hash: str, role: str = "student") -> User: ...

class IPasswordHasher:
    def hash(self, plain: str) -> str: ...

class RegisterUser:
    def __init__(self, repo: IUserRepository, hasher: IPasswordHasher):
        self.repo = repo
        self.hasher = hasher

    def execute(self, email: str, password: str) -> User:
        if "@" not in email:
            raise ValueError("Invalid email")
        if self.repo.get_by_email(email):
            raise ValueError("Email already registered")
        pwd_hash = self.hasher.hash(password)
        return self.repo.create(email, pwd_hash)
