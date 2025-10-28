from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class DocumentBase(BaseModel):
    filename: str
    status: str
    error_message: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    status: Optional[str] = None
    error_message: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
