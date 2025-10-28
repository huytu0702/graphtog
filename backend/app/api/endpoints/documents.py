from fastapi import APIRouter, Depends, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.postgres import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.auth import get_current_user
from app.services.document_processor import process_document

router = APIRouter(tags=["documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate file type - only .md files are allowed
    if not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Only Markdown (.md) files are allowed")

    # Additional check: ensure that the file has a .md extension
    if not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Only Markdown (.md) files are allowed")

    # Save file to a temporary location
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    # Create document record in database with status 'processing'
    db_document = Document(
        filename=file.filename,
        file_path=file_location,
        status="processing",
        user_id=current_user.id,
        file_type="md",
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
    current_user: User = Depends(get_current_user),
):
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return documents


@router.get("/list", response_model=List[DocumentResponse])
def list_documents_alias(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all documents for the current user (alias for GET /)

    Args:
        skip: Number of documents to skip
        limit: Maximum number of documents to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of user's documents
    """
    return list_documents(skip, limit, db, current_user)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.get("/{document_id}/status")
def get_document_status(
    document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get the processing status of a document

    Args:
        document_id: ID of the document
        db: Database session
        current_user: Current authenticated user

    Returns:
        Document status information
    """
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "created_at": document.created_at.isoformat() if document.created_at else None,
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}
