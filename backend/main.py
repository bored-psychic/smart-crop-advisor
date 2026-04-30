import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from api.router import router as api_router
from core.config import settings

app = FastAPI(
    title="KisanOS API",
    description="High-performance, zero-latency asynchronous backend for Smart Crop Advisor.",
    version="2.0.0"
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Performance Monitoring Middleware ──────────────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "timestamp": time.time()}

# ── API Routes ────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
