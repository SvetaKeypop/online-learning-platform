from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
from fastapi.responses import Response as FastAPIResponse

# Метрики для HTTP запросов
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Метрики для кэша
cache_hits_total = Counter('cache_hits_total', 'Total cache hits')
cache_misses_total = Counter('cache_misses_total', 'Total cache misses')

# Метрики для БД
db_queries_total = Counter('db_queries_total', 'Total database queries')
db_query_duration_seconds = Histogram('db_query_duration_seconds', 'Database query duration in seconds')

# Метрики для активных соединений
active_connections = Gauge('active_connections', 'Active database connections')

def metrics_endpoint():
    """Endpoint для Prometheus метрик"""
    return Response(content=generate_latest(), media_type="text/plain")

