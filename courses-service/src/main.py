import time
import logging
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .infrastructure.db import engine
from .infrastructure.models import Base
from .infrastructure.metrics import (
    metrics_endpoint,
    http_requests_total,
    http_request_duration_seconds
)
from .interfaces.http.routers import courses as courses_router
from .config import settings

# Настройка структурированного логирования
log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(title="Courses Service", version="0.1.0")

# Добавляем middleware для правильной кодировки и метрик
@app.middleware("http")
async def add_charset_header(request: Request, call_next):
    start_time = time.time()
    method = request.method
    path = request.url.path
    
    response = await call_next(request)
    
    if response.headers.get("content-type", "").startswith("application/json"):
        response.headers["content-type"] = "application/json; charset=utf-8"
    
    # Метрики
    duration = time.time() - start_time
    status_code = response.status_code
    http_requests_total.labels(method=method, endpoint=path, status=status_code).inc()
    http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)
    
    # Логирование
    logger.info(
        "http_request",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2)
    )
    
    return response


@app.on_event("startup")
def on_startup():
    logger.info("Starting courses service", version="0.1.0")
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Database connection established")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()


app.include_router(courses_router.router)
