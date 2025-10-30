"""
Pydantic schemas for Claim-related API requests and responses
"""

from typing import Optional
from pydantic import BaseModel, Field


class ClaimBase(BaseModel):
    """Base Claim schema with common fields"""

    subject: str = Field(..., description="Subject entity name")
    object: str = Field(..., description="Object entity name or NONE")
    claim_type: str = Field(..., description="Type/category of claim")
    status: str = Field(..., description="TRUE, FALSE, or SUSPECTED")
    description: str = Field(..., description="Detailed claim description")
    start_date: Optional[str] = Field(None, description="Claim start date (ISO-8601)")
    end_date: Optional[str] = Field(None, description="Claim end date (ISO-8601)")
    source_text: Optional[str] = Field(None, description="Source text supporting the claim")


class ClaimCreate(ClaimBase):
    """Schema for creating a new claim"""

    pass


class ClaimResponse(ClaimBase):
    """Schema for claim response"""

    id: str = Field(..., description="Claim ID")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

    class Config:
        from_attributes = True


class ClaimQueryRequest(BaseModel):
    """Schema for querying claims"""

    entity_name: Optional[str] = Field(None, description="Filter by entity name")
    claim_type: Optional[str] = Field(None, description="Filter by claim type")
    status: Optional[str] = Field(None, description="Filter by status (TRUE/FALSE/SUSPECTED)")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of claims to return")


class ClaimQueryResponse(BaseModel):
    """Schema for claim query results"""

    status: str = Field(..., description="success or error")
    total: int = Field(..., description="Total number of claims found")
    claims: list[ClaimResponse] = Field(..., description="List of claims")
    entity_name: Optional[str] = Field(None, description="Entity name if filtered by entity")


class ClaimExtractionRequest(BaseModel):
    """Schema for manual claim extraction request"""

    text: str = Field(..., description="Text to extract claims from")
    entity_specs: Optional[str] = Field(
        None, description="Entity specification (names or types)"
    )
    claim_description: Optional[str] = Field(
        None, description="Description of claims to extract"
    )


class ClaimExtractionResponse(BaseModel):
    """Schema for claim extraction results"""

    status: str = Field(..., description="success or error")
    claims: list[ClaimBase] = Field(..., description="List of extracted claims")
    error: Optional[str] = Field(None, description="Error message if status is error")
