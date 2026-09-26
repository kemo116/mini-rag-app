from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match
import time

# Metric names/labels match the Grafana dashboard (http_requests_total, path, status, app_name)
APP_NAME = "mini-rag-app"

APP_INFO = Gauge('fastapi_app_info', 'FastAPI application info', ['app_name'])
APP_INFO.labels(app_name=APP_NAME).set(1)

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'path', 'status', 'app_name'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Duration of HTTP Latency', ['method', 'path', 'app_name'])


def _get_path(request: Request) -> str:
    # use the route template (e.g. /api/v1/nlp/{project_id}) to keep label cardinality low
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - start_time
            path = _get_path(request)
            REQUEST_LATENCY.labels(method=request.method, path=path, app_name=APP_NAME).observe(duration)
            REQUEST_COUNT.labels(method=request.method, path=path, status=status_code, app_name=APP_NAME).inc()


def setup_metrics(app: FastAPI):
    app.add_middleware(PrometheusMiddleware)

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
