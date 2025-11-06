"""
Tree of Graphs (ToG) API schemas and Pydantic models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID


class ToGConfigSchema(BaseModel):
    """Configuration for ToG reasoning parameters."""

    search_width: int = Field(default=3, description="Max entities to explore per depth level")
    search_depth: int = Field(default=3, description="Max traversal depth")
    num_retain_entity: int = Field(default=5, description="Max entities to retain during search")
    exploration_temp: float = Field(default=0.4, description="Temperature for exploration phase")
    reasoning_temp: float = Field(default=0.0, description="Temperature for reasoning phase")
    pruning_method: str = Field(default="llm", description="llm, bm25, or sentence_bert")
    enable_sufficiency_check: bool = Field(default=True, description="Enable sufficiency evaluation")


class ToGEntitySchema(BaseModel):
    """Entity representation for ToG reasoning."""

    id: str = Field(description="Unique entity identifier")
    name: str = Field(description="Entity name")
    type: str = Field(description="Entity type (PERSON, ORGANIZATION, etc.)")
    description: Optional[str] = Field(default=None, description="Entity description")
    confidence: float = Field(default=1.0, description="Entity confidence score")
    document_id: Optional[int] = Field(default=None, description="Source document ID")


class ToGRelationSchema(BaseModel):
    """Relation representation for ToG reasoning."""

    type: str = Field(description="Relation type")
    source_entity: ToGEntitySchema = Field(description="Source entity")
    target_entity: ToGEntitySchema = Field(description="Target entity")
    description: Optional[str] = Field(default=None, description="Relation description")
    confidence: float = Field(default=1.0, description="Relation confidence score")
    score: float = Field(default=0.0, description="LLM-assigned relevance score")


class ToGReasoningStepSchema(BaseModel):
    """Single step in ToG reasoning path."""

    depth: int = Field(description="Traversal depth level")
    entities_explored: List[ToGEntitySchema] = Field(description="Entities explored at this depth")
    relations_selected: List[ToGRelationSchema] = Field(description="Relations selected for exploration")
    sufficiency_score: Optional[float] = Field(default=None, description="Sufficiency evaluation score")
    reasoning_notes: Optional[str] = Field(default=None, description="Reasoning notes")


class ToGTripletSchema(BaseModel):
    """Knowledge triplet schema."""

    subject: str = Field(description="Subject entity")
    relation: str = Field(description="Relation type")
    object: str = Field(description="Object entity")
    confidence: float = Field(default=1.0, description="Triplet confidence")
    source: Optional[str] = Field(default=None, description="Source of triplet")


class ToGReasoningPathSchema(BaseModel):
    """Complete ToG reasoning path."""

    steps: List[ToGReasoningStepSchema] = Field(default_factory=list, description="Reasoning steps")
    final_answer: Optional[str] = Field(default=None, description="Final generated answer")
    confidence_score: float = Field(default=0.0, description="Overall confidence score")
    sufficiency_status: str = Field(default="unknown", description="Sufficiency status: unknown, sufficient, insufficient")
    retrieved_triplets: List[ToGTripletSchema] = Field(default_factory=list, description="Retrieved knowledge triplets")


class ToGQueryRequest(BaseModel):
    """Request schema for ToG query endpoint."""

    question: str = Field(description="User question to answer")
    document_ids: Optional[List[int]] = Field(default=None, description="Filter to specific document IDs")
    config: ToGConfigSchema = Field(default_factory=ToGConfigSchema, description="ToG configuration")


class ToGQueryResponse(BaseModel):
    """Response schema for ToG query endpoint."""

    answer: str = Field(description="Generated answer")
    reasoning_path: ToGReasoningPathSchema = Field(description="Complete reasoning path")
    query_type: str = Field(default="tog", description="Query type identifier")
    confidence_score: float = Field(description="Answer confidence score")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")
    query_id: Optional[str] = Field(default=None, description="Database query ID for visualization")


class ToGExplainRequest(BaseModel):
    """Request schema for ToG explanation endpoint."""

    query_id: UUID = Field(description="Query ID to explain")


class ToGExplainResponse(BaseModel):
    """Response schema for ToG explanation endpoint."""

    query_id: UUID = Field(description="Query ID")
    reasoning_path: ToGReasoningPathSchema = Field(description="Detailed reasoning path")
    visualization_data: Optional[Dict[str, Any]] = Field(default=None, description="Data for visualization")


class ToGConfigRequest(BaseModel):
    """Request schema for ToG configuration endpoint."""

    config: ToGConfigSchema = Field(description="ToG configuration to validate/set")


class ToGConfigResponse(BaseModel):
    """Response schema for ToG configuration endpoint."""

    config: ToGConfigSchema = Field(description="Validated ToG configuration")
    is_valid: bool = Field(description="Whether configuration is valid")
    validation_errors: Optional[List[str]] = Field(default=None, description="Validation error messages")
