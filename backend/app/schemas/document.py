from pydantic import BaseModel
from datetime import datetime
from typing import Optional


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
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True