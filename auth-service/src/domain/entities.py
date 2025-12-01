from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    id: int | None
    email: str
    role: str = "student"
