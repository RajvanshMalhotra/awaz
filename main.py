import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.onboarding import router as onboarding_router
from api.pipeline import router as pipeline_router
from core.session_store import session_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background task: purge expired sessions every 5 minutes
    async def purge_loop():
        while True:
            await asyncio.sleep(300)
            count = session_store.purge_expired()
            if count:
                print(f"[session_store] Purged {count} expired sessions")

    task = asyncio.create_task(purge_loop())
    yield
    task.cancel()


app = FastAPI(
    title="Awaaz API",
    description="Voice → expressive text → TTS pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allows the Next.js frontend on any localhost port during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        # Add your production domain here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboarding_router)
app.include_router(pipeline_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "awaaz-api"}


@app.get("/")
async def root():
    return {
        "service": "Awaaz API",
        "docs": "/docs",
        "endpoints": {
            "process": "POST /pipeline/process",
            "approve": "POST /pipeline/approve",
            "deny": "POST /pipeline/deny",
            "save_speaker": "POST /pipeline/save-speaker",
            "onboarding_status": "GET /onboarding/status",
            "save_onboarding": "POST /onboarding",
            "clear_onboarding": "DELETE /onboarding",
        },
    }
