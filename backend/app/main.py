from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.mongo import connect_to_mongo, close_mongo_connection
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title="AI Resume Analyzer API",
    description="Semantic resume matching, Gemini-powered resume feedback, and AI mock interviews.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "AI Resume Analyzer API is running",
        "version": "2.0.0",
        "docs": "/docs",
        "ai_status": {
            "gemini_configured": bool(settings.gemini_api_key),
            "semantic_model": settings.embedding_model,
        },
    }
