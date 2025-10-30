"""
Pydantic schemas for entity resolution and disambiguation
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class EntityInfo(BaseModel):
    """Entity information"""

    id: str
    name: str
    type: str
    description: Optional[str] = None
    confidence: Optional[float] = None
    mention_count: Optional[int] = None


class SimilarEntityResponse(EntityInfo):
    """Response for similar entity search"""

    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class FindSimilarEntitiesRequest(BaseModel):
    """Request to find similar entities"""

    entity_name: str = Field(..., min_length=1, description="Entity name to search for")
    entity_type: str = Field(..., min_length=1, description="Entity type (PERSON, ORGANIZATION, etc.)")
    threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Similarity threshold (0.0-1.0), defaults to 0.85"
    )


class FindSimilarEntitiesResponse(BaseModel):
    """Response with similar entities"""

    status: str
    query: Dict[str, str]
    similar_entities: List[SimilarEntityResponse]
    count: int


class DuplicatePair(BaseModel):
    """A pair of potentially duplicate entities"""

    entity1: EntityInfo
    entity2: EntityInfo
    similarity: float = Field(..., ge=0.0, le=1.0)


class FindDuplicatesRequest(BaseModel):
    """Request to find duplicate entities"""

    entity_type: Optional[str] = Field(None, description="Filter by entity type (optional)")
    threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Similarity threshold (0.0-1.0), defaults to 0.85"
    )


class FindDuplicatesResponse(BaseModel):
    """Response with duplicate entity pairs"""

    status: str
    duplicate_pairs: List[DuplicatePair]
    count: int
    threshold: float


class LLMResolutionRequest(BaseModel):
    """Request for LLM-based entity resolution"""

    entity1_id: str = Field(..., description="First entity ID")
    entity2_id: str = Field(..., description="Second entity ID")


class LLMResolutionResponse(BaseModel):
    """Response from LLM-based resolution"""

    status: str
    are_same: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    suggested_canonical_name: Optional[str] = None
    entity1: EntityInfo
    entity2: EntityInfo
    error: Optional[str] = None


class MergeEntitiesRequest(BaseModel):
    """Request to merge duplicate entities"""

    primary_entity_id: str = Field(..., description="ID of entity to keep")
    duplicate_entity_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of entity IDs to merge into primary"
    )
    canonical_name: Optional[str] = Field(
        None,
        description="Optional canonical name for merged entity"
    )

    @field_validator("duplicate_entity_ids")
    @classmethod
    def validate_duplicates(cls, v, info):
        """Ensure primary_entity_id is not in duplicate_entity_ids"""
        if "primary_entity_id" in info.data and info.data["primary_entity_id"] in v:
            raise ValueError("primary_entity_id cannot be in duplicate_entity_ids")
        return v


class MergeEntitiesResponse(BaseModel):
    """Response from entity merge operation"""

    status: str
    primary_entity_id: str
    merged_count: int
    aliases: List[str]
    canonical_name: Optional[str] = None
    error: Optional[str] = None


class AddAliasRequest(BaseModel):
    """Request to add an alias to an entity"""

    entity_id: str = Field(..., description="Entity ID")
    alias: str = Field(..., min_length=1, description="Alias name to add")


class AddAliasResponse(BaseModel):
    """Response from adding an alias"""

    status: str
    entity_id: str
    alias: str
    all_aliases: List[str]


class GetAliasesRequest(BaseModel):
    """Request to get entity aliases"""

    entity_id: str = Field(..., description="Entity ID")


class GetAliasesResponse(BaseModel):
    """Response with entity aliases"""

    status: str
    entity_id: str
    canonical_name: str
    aliases: List[str]


class EntityResolutionStats(BaseModel):
    """Statistics about entity resolution"""

    total_entities: int
    entities_with_aliases: int
    total_aliases: int
    potential_duplicates_count: int
    threshold_used: float
