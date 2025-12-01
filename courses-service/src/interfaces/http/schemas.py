from pydantic import BaseModel

class CourseCreate(BaseModel):
    title: str
    description: str | None = None

class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None

class CourseOut(BaseModel):
    id: int
    title: str
    description: str | None = None
    class Config: from_attributes = True
