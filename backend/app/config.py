"""
Configuration module for FastAPI application
Loads environment variables and provides centralized configuration
"""

import os
from functools import lru_cache
from typing import Optional


class Settings:
    """Application settings loaded from environment variables"""

    # ========== BACKEND CONFIG ==========
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # ========== DATABASE - PostgreSQL ==========
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://graphtog_user:graphtog_password@postgres:5432/graphtog_db",
    )
    SQLALCHEMY_ECHO: bool = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"

    # ========== DATABASE - Neo4j ==========
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "graphtog_password")

    # ========== CACHE - Redis ==========
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    # ========== AI/LLM - Google Gemini ==========
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ========== DOCUMENT PROCESSING CONFIG ==========
    # Direct MD file processing - no external services needed

    # ========== FILE UPLOAD CONFIG ==========
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "52428800"))  # 50MB
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    ALLOWED_DOCUMENT_TYPES: list = os.getenv(
        "ALLOWED_DOCUMENT_TYPES", "md"
    ).split(",")

    # ========== LANGSMITH CONFIG ==========
    LANGSMITH_API_KEY: Optional[str] = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "graphtog-project")

    # ========== LOGGING ==========
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        """Initialize settings and create upload directory if it doesn't exist"""
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Cached settings getter - use this to get settings throughout the app"""
    return Settings()
