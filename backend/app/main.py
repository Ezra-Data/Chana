"""
Smart Campus Companion — FastAPI Application Entry Point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, async_session
from app.seed_data import seed_database

# Import all routers
from app.routers import auth, admin, chat, tickets, navigation, knowledge, websocket, analytics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting Smart Campus Companion API...")
    await init_db()
    logger.info("Database tables created.")

    # Seed data on first run
    async with async_session() as db:
        await seed_database(db)
        # Ensure ChromaDB vector store is populated
        from app.services import rag_service
        vector_stats = rag_service.get_collection_stats()
        if vector_stats.get("total_chunks", 0) == 0:
            logger.info("ChromaDB vector store is empty — syncing from knowledge_entries...")
            from sqlalchemy import select
            from app.models.knowledge import KnowledgeEntry
            kb_res = await db.execute(select(KnowledgeEntry))
            entries = kb_res.scalars().all()
            for entry in entries:
                rag_service.add_document(
                    entry_id=entry.id,
                    title=entry.title,
                    content=entry.content,
                    category=entry.category,
                    source_doc=entry.source_doc,
                )
            logger.info(f"Synchronized {len(entries)} KB entries into ChromaDB vector store.")

    logger.info("Application ready!")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Smart Campus Companion API",
    description="Unified AI-powered campus support platform — chatbot, tickets, navigation, and admin.",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ─────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ───────────────────────────────────────

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(navigation.router)
app.include_router(knowledge.router)
app.include_router(analytics.router)
app.include_router(websocket.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Smart Campus Companion API",
        "deepseek_configured": bool(settings.DEEPSEEK_API_KEY),
    }
