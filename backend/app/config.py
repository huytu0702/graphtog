"""
Configuration module for FastAPI application
Loads environment variables and provides centralized configuration
"""

import os
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

# Load .env file from backend directory
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""

    # ========== BACKEND CONFIG ==========
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    # Increased from 30 to 1440 minutes (24 hours) to prevent token expiration during active sessions
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

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
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    # ========== QUERY PROCESSING CONFIG ==========
    # Map-Reduce settings for global search optimization
    ENABLE_MAPREDUCE: bool = os.getenv("ENABLE_MAPREDUCE", "True").lower() == "true"
    MAPREDUCE_BATCH_SIZE: int = int(os.getenv("MAPREDUCE_BATCH_SIZE", "10"))
    # Threshold for using Map-Reduce (number of communities)
    MAPREDUCE_THRESHOLD: int = int(os.getenv("MAPREDUCE_THRESHOLD", "20"))

    # ========== ENTITY RESOLUTION CONFIG ==========
    # Enable automatic entity resolution during document processing
    ENABLE_ENTITY_RESOLUTION: bool = os.getenv("ENABLE_ENTITY_RESOLUTION", "False").lower() == "true"
    # Similarity threshold for fuzzy matching (0.0-1.0)
    ENTITY_SIMILARITY_THRESHOLD: float = float(os.getenv("ENTITY_SIMILARITY_THRESHOLD", "0.85"))
    # Use LLM for ambiguous entity resolution (more accurate but slower)
    ENABLE_LLM_ENTITY_RESOLUTION: bool = os.getenv("ENABLE_LLM_ENTITY_RESOLUTION", "False").lower() == "true"
    # Automatically merge entities above this confidence threshold (0.0-1.0)
    AUTO_MERGE_CONFIDENCE_THRESHOLD: float = float(os.getenv("AUTO_MERGE_CONFIDENCE_THRESHOLD", "0.95"))

    # ========== DOCUMENT PROCESSING CONFIG ==========
    # Direct MD file processing - no external services needed

    # ========== FILE UPLOAD CONFIG ==========
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "52428800"))  # 50MB
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    ALLOWED_DOCUMENT_TYPES: list = os.getenv("ALLOWED_DOCUMENT_TYPES", "md").split(",")

    # ========== LANGSMITH CONFIG ==========
    LANGSMITH_API_KEY: Optional[str] = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "graphtog-project")

    # ========== LOGGING ==========
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        """Initialize settings and create upload directory if it doesn't exist"""
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        self._validate_critical_settings()

    def _validate_critical_settings(self):
        """Validate that critical settings are configured"""
        import logging

        logger = logging.getLogger(__name__)

        if not self.GOOGLE_API_KEY:
            logger.warning(
                "⚠️  GOOGLE_API_KEY is not configured!\n"
                "   Get your key from: https://ai.google.dev/\n"
                "   Then set it in environment variable: GOOGLE_API_KEY=your_key_here\n"
                "   Or create a .env file in the backend directory with:\n"
                "   GOOGLE_API_KEY=your_key_here"
            )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings getter - use this to get settings throughout the app"""
    return Settings()
