from pydantic import BaseModel

class ProgressItem(BaseModel):
    lesson_id: int
    completed_at: str

class CompleteResp(BaseModel):
    ok: bool
    lesson_id: int
