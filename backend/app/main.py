from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, categories, entries, reports, settings, dashboard

app = FastAPI(title="SkillTracer API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://skilltracer.art-artel.su",
        "https://tma.skilltracer.art-artel.su",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(entries.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "SkillTracer API is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
