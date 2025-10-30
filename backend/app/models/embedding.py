"""
Text embedding model stored in PostgreSQL with pgvector
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from pgvector.sqlalchemy import Vector

from app.db.postgres import Base


class TextEmbedding(Base):
    """Persisted text chunk embeddings for hybrid search"""

    __tablename__ = "text_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id = Column(String(255), nullable=False, unique=True, index=True)
    text = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=True)
    end_char = Column(Integer, nullable=True)
    embedding = Column(Vector(2048), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<TextEmbedding(chunk_id={self.chunk_id}, document_id={self.document_id})>"

