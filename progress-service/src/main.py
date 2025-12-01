from fastapi import FastAPI
from sqlalchemy import text
from .infrastructure.db import engine
from .infrastructure.models import Base
from .interfaces.http.routers import progress as progress_router

app = FastAPI(title="Progress Service", version="0.1.0")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

@app.get("/health")
def health(): return {"status":"ok"}

app.include_router(progress_router.router)
