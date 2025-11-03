"""
Embedding service for generating and storing Gemini embeddings in pgvector
"""

import asyncio
import logging
import time
from typing import Dict, List, Sequence
from uuid import UUID

import google.generativeai as genai
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.embedding import TextEmbedding

logger = logging.getLogger(__name__)

settings = get_settings()

if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
else:  # pragma: no cover - configuration safeguard
    logger.warning("GOOGLE_API_KEY not configured. Embedding generation will fail.")


class EmbeddingService:
    """Service for generating Gemini embeddings and persisting them with pgvector"""

    def __init__(self) -> None:
        self.model_name = "gemini-embedding-001"  # Gemini gemini-embedding-001 (2048 dimensions)
        self.max_retries = 3
        self.retry_delay_seconds = 1.0
        self.rate_limit_delay = 0.05
        self._last_request_time = 0.0

    def _apply_rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    @staticmethod
    def _coerce_document_id(document_id) -> UUID:
        if isinstance(document_id, UUID):
            return document_id
        return UUID(str(document_id))

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector using Gemini gemini-embedding-001 model
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        payload = text.strip()

        for attempt in range(self.max_retries):
            try:
                self._apply_rate_limit()
                response = genai.embed_content(
                    model=self.model_name,
                    content=payload,
                    task_type="SEMANTIC_SIMILARITY",
                )
                embedding = response.get("embedding")
                if not embedding:
                    raise RuntimeError("Embedding response missing vector")
                if len(embedding) != 3072:
                    logger.warning("Unexpected embedding length %s (expected 3072)", len(embedding))
                return list(embedding)
            except Exception as exc:  # pragma: no cover - external service errors
                wait_time = self.retry_delay_seconds * (2**attempt)
                logger.warning(
                    "Embedding attempt %s failed: %s; retrying in %.2fs",
                    attempt + 1,
                    exc,
                    wait_time,
                )
                time.sleep(wait_time)

        raise RuntimeError("Failed to generate embedding after retries")

    def _upsert_embedding(
        self,
        db: Session,
        *,
        document_id: UUID,
        chunk_id: str,
        text: str,
        start_char: int | None,
        end_char: int | None,
        embedding: List[float],
    ) -> None:
        existing = db.query(TextEmbedding).filter_by(chunk_id=chunk_id).one_or_none()

        if existing:
            existing.document_id = document_id
            existing.text = text
            existing.start_char = start_char
            existing.end_char = end_char
            existing.embedding = embedding
        else:
            record = TextEmbedding(
                document_id=document_id,
                chunk_id=chunk_id,
                text=text,
                start_char=start_char,
                end_char=end_char,
                embedding=embedding,
            )
            db.add(record)

    async def generate_and_store_embeddings(
        self,
        db: Session,
        *,
        document_id,
        chunks: Sequence[Dict[str, int | str | None]],
    ) -> Dict[str, int]:
        """
        Generate embeddings for document chunks and persist them in PostgreSQL
        """
        doc_id = self._coerce_document_id(document_id)
        embedded = 0
        skipped = 0

        for chunk in chunks:
            text = str(chunk.get("text") or "").strip()
            chunk_id = str(chunk.get("chunk_id") or "")

            if not text or not chunk_id:
                skipped += 1
                continue

            try:
                vector = self.generate_embedding(text)
            except Exception as exc:
                logger.error("Embedding generation failed for chunk %s: %s", chunk_id, exc)
                skipped += 1
                continue

            self._upsert_embedding(
                db,
                document_id=doc_id,
                chunk_id=chunk_id,
                text=text,
                start_char=chunk.get("start_char"),
                end_char=chunk.get("end_char"),
                embedding=vector,
            )
            embedded += 1

            # Gentle pacing between requests
            await asyncio.sleep(self.rate_limit_delay)

        try:
            db.commit()
        except SQLAlchemyError as exc:
            db.rollback()
            raise RuntimeError(f"Failed to persist embeddings: {exc}") from exc

        return {"embedded": embedded, "skipped": skipped}


# Export singleton instance
embedding_service = EmbeddingService()
