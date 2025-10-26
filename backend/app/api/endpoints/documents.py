from fastapi import APIRouter, Depends, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from backend.app.db.postgres import get_db
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.schemas.document import DocumentResponse
from backend.app.services.auth import get_current_user
from backend.app.services.document_processor import process_document

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate file type
    allowed_types = ["application/pdf", "application/msword", 
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     "text/plain"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Save file to a temporary location
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    
    # Create document record in database with status 'processing'
    db_document = Document(
        filename=file.filename,
        file_path=file_location,
        status="processing",
        user_id=current_user.id
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    # Process document in background
    background_tasks.add_task(process_document, db_document.id, file_location, db)
    
    return {"id": db_document.id, "filename": db_document.filename, "status": db_document.status}

@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    documents = db.query(Document).filter(Document.user_id == current_user.id).offset(skip).limit(limit).all()
    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}