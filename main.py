import time
import uuid
import collections
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse, JSONResponse

# ---------------------------------------------------------------------------
# App & state
# ---------------------------------------------------------------------------
app = FastAPI()

START_TIME = time.time()

# Prometheus counter – simple integer, incremented on every request via middleware
http_requests_total: int = 0

# Structured log ring-buffer (last 1000 entries)
LOG_BUFFER: collections.deque = collections.deque(maxlen=1000)


# ---------------------------------------------------------------------------
# Middleware – runs on EVERY request
# ---------------------------------------------------------------------------
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    global http_requests_total
    http_requests_total += 1

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)

    # Structured log entry
    LOG_BUFFER.append({
        "level": "info",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
    })

    return response


# ---------------------------------------------------------------------------
# GET /work?n=K
# ---------------------------------------------------------------------------
@app.get("/work")
async def work(n: int = Query(default=1)):
    return {"email": "_", "done": n}


# ---------------------------------------------------------------------------
# GET /metrics  – Prometheus exposition format
# ---------------------------------------------------------------------------
@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    body = (
        "# HELP http_requests_total Total HTTP requests received.\n"
        "# TYPE http_requests_total counter\n"
        f"http_requests_total {http_requests_total}\n"
    )
    return PlainTextResponse(body, media_type="text/plain; version=0.0.4; charset=utf-8")


# ---------------------------------------------------------------------------
# GET /healthz
# ---------------------------------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "uptime_s": round(time.time() - START_TIME, 3)}


# ---------------------------------------------------------------------------
# GET /logs/tail?limit=N
# ---------------------------------------------------------------------------
@app.get("/logs/tail")
async def logs_tail(limit: int = Query(default=20)):
    entries = list(LOG_BUFFER)[-limit:]
    return JSONResponse(content=entries)
