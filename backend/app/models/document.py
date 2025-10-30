"""
Document model for PostgreSQL database
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.postgres import Base


class DocumentStatus:
    """Document processing status constants"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    VALID_STATUSES = [PENDING, PROCESSING, COMPLETED, FAILED]


class Document(Base):
    """Document database model"""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default=DocumentStatus.PENDING, index=True)
    file_size = Column(BigInteger, nullable=True)  # File size in bytes
    file_type = Column(String(20), nullable=True)  # md
    error_message = Column(String(500), nullable=True)  # Error message if processing failed

    # Incremental indexing fields
    version = Column(Integer, nullable=False, default=1)  # Document version for tracking updates
    content_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash of content
    last_processed_at = Column(DateTime, nullable=True)  # Last successful processing timestamp

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")
    queries = relationship("Query", back_populates="document")
    embeddings = relationship(
        "TextEmbedding",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
