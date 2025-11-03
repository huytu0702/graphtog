"""
Query model for PostgreSQL database
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from app.db.postgres import Base


class Query(Base):
    """Query database model for storing user questions and answers"""

    __tablename__ = "queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True, index=True)
    query_text = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    reasoning_chain = Column(Text, nullable=True)  # JSON string with reasoning steps
    query_mode = Column(String(20), nullable=True)  # graphrag, tog, hybrid (Phase 4)
    confidence_score = Column(Float, nullable=True)  # Confidence of the answer
    processing_time_ms = Column(Integer, nullable=True)  # Processing time in milliseconds
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ToG-specific fields
    tog_config = Column(JSON, nullable=True)  # ToG configuration used
    reasoning_path = Column(JSON, nullable=True)  # Complete reasoning path
    retrieved_triplets = Column(JSON, nullable=True)  # Retrieved knowledge triplets

    # Relationships
    user = relationship("User", back_populates="queries")
    document = relationship("Document", back_populates="queries")

    def __repr__(self) -> str:
        return f"<Query(id={self.id}, user_id={self.user_id}, created_at={self.created_at})>"
