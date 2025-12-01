from pydantic import BaseModel, EmailStr

class RegisterReq(BaseModel):
    email: EmailStr
    password: str

class LoginReq(BaseModel):
    email: EmailStr
    password: str

class UserResp(BaseModel):
    id: int
    email: EmailStr
    role: str

class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"
