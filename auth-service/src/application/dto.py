from dataclasses import dataclass

@dataclass
class RegisterUserInput:
    email: str
    password: str

@dataclass
class UserDTO:
    id: int
    email: str
    role: str
