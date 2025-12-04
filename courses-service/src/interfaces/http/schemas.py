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

class LessonCreate(BaseModel):
    title: str
    content: str
    order: int = 0

class LessonUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    order: int | None = None

class LessonOut(BaseModel):
    id: int
    course_id: int
    title: str
    content: str
    order: int
    class Config: from_attributes = True