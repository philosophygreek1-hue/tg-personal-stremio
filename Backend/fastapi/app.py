"""
app.py — FastAPI application setup.
REUSED from original: router registration pattern, CORS, static files.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from Backend.fastapi.routes import stremio_routes, admin_routes, stream_routes

app = FastAPI(title="Personal Video Stremio Server", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stremio addon routes — mounted at /stremio/{token}/...
app.include_router(stremio_routes.router, prefix="/stremio")

# Streaming endpoint — /dl/{encoded_id}/video.mkv
app.include_router(stream_routes.router)

# Admin panel
app.include_router(admin_routes.router)


@app.get("/")
async def root():
    return {"status": "Personal Video Stremio Server is running"}
