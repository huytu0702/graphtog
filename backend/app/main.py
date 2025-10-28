"""
FastAPI main application module
Initialize FastAPI app with configuration, database connections, and routes
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db.neo4j import close_neo4j, init_neo4j
from app.db.postgres import init_db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app
    Handles startup and shutdown events
    """
    # Startup event
    logger.info("🚀 Starting GraphToG application...")

    # Initialize PostgreSQL
    try:
        init_db()
        logger.info("✅ PostgreSQL database initialized")
    except Exception as e:
        logger.error(f"❌ PostgreSQL initialization error: {str(e)}")

    # Initialize Neo4j
    try:
        init_neo4j()
        logger.info("✅ Neo4j graph database initialized")
    except Exception as e:
        logger.error(f"❌ Neo4j initialization error: {str(e)}")

    # Initialize graph schema
    try:
        from app.services.graph_service import graph_service

        if graph_service.init_schema():
            logger.info("✅ Graph schema initialized")
        else:
            logger.warning("⚠️ Graph schema initialization returned False")
    except Exception as e:
        logger.error(f"❌ Graph schema initialization error: {str(e)}")

    yield

    # Shutdown event
    logger.info("🛑 Shutting down GraphToG application...")
    try:
        close_neo4j()
        logger.info("✅ Neo4j connection closed")
    except Exception as e:
        logger.error(f"⚠️ Neo4j shutdown warning: {str(e)}")


# Create FastAPI app
app = FastAPI(
    title="GraphToG Backend",
    description="GraphRAG-based document processing with Tree of Graphs reasoning",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add exception handler for HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "graphtog-backend",
        "version": "0.1.0",
    }


# Info endpoint
@app.get("/info")
async def app_info():
    """Application information endpoint"""
    return {
        "name": "GraphToG Backend",
        "description": "GraphRAG-based document processing with Tree of Graphs reasoning",
        "version": "0.1.0",
        "debug_mode": settings.DEBUG,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to GraphToG Backend API",
        "docs": "/docs",
        "health": "/health",
    }


from app.api.endpoints import (
    auth,
    documents,
    queries,
    admin,
    communities,
    advanced_features,
    visualization,
    cache,
    retrieval,
    analyze,
)

# Include API routes
app.include_router(auth.router, prefix="/api/auth")
app.include_router(documents.router, prefix="/api/documents")
app.include_router(queries.router, prefix="/api/queries")
app.include_router(admin.router, prefix="/api/admin")
app.include_router(communities.router, prefix="/api/communities")
app.include_router(advanced_features.router, prefix="/api/extract")
app.include_router(visualization.router, prefix="/api/visualize")
app.include_router(cache.router, prefix="/api/cache")
app.include_router(retrieval.router, prefix="/api/retrieve")
app.include_router(analyze.router, prefix="/api/analyze")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
