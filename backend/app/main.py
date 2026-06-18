from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth

app = FastAPI(title="SkillTracer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "SkillTracer API is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
