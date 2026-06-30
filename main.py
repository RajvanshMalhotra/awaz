# import asyncio
# from contextlib import asynccontextmanager

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles

# from api.onboarding import router as onboarding_router
# from api.pipeline import router as pipeline_router
# from core.session_store import session_store


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Background task: purge expired sessions every 5 minutes
#     async def purge_loop():
#         while True:
#             await asyncio.sleep(300)
#             count = session_store.purge_expired()
#             if count:
#                 print(f"[session_store] Purged {count} expired sessions")

#     task = asyncio.create_task(purge_loop())
#     yield
#     task.cancel()


# app = FastAPI(
#     title="Awaaz API",
#     description="Voice → expressive text → TTS pipeline",
#     version="1.0.0",
#     lifespan=lifespan,
# )

# # CORS — allows the Next.js frontend on any localhost port during dev
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:3000",
#         "http://localhost:3001",
#         "http://localhost:5173",
#         "http://127.0.0.1:3000",
#         "http://127.0.0.1:5173",
#         # Add your production domain here
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.mount("/tts_output", StaticFiles(directory="tts_output"), name="tts_output")
# app.include_router(onboarding_router)
# app.include_router(pipeline_router)


# @app.get("/health")
# async def health():
#     return {"status": "ok", "service": "awaaz-api"}


# @app.get("/")
# async def root():
#     return {
#         "service": "Awaaz API",
#         "docs": "/docs",
#         "endpoints": {
#             "process": "POST /pipeline/process",
#             "approve": "POST /pipeline/approve",
#             "deny": "POST /pipeline/deny",
#             "save_speaker": "POST /pipeline/save-speaker",
#             "onboarding_status": "GET /onboarding/status",
#             "save_onboarding": "POST /onboarding",
#             "clear_onboarding": "DELETE /onboarding",
#         },
#     }
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.ambient_ws import router as ambient_ws_router
from api.onboarding import router as onboarding_router
from api.pipeline import router as pipeline_router
from api.ws import router as ws_router
from core.session_store import session_store


@asynccontextmanager
async def lifespan(app: FastAPI):
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

_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
_extra_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        *_extra_origins,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path("tts_output").mkdir(exist_ok=True)
app.mount("/tts_output", StaticFiles(directory="tts_output"), name="tts_output")

app.include_router(onboarding_router)
app.include_router(pipeline_router)
app.include_router(ws_router)
app.include_router(ambient_ws_router)

# Serve built React SPA — assets at /assets, catch-all returns index.html
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend-assets")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "awaaz-api"}


@app.get("/")
async def root():
    index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"service": "Awaaz API", "docs": "/docs"}