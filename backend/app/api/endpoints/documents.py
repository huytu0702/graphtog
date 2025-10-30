from fastapi import APIRouter, Depends, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import asyncio

from app.db.postgres import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse
from app.services.auth import get_current_user
from app.services.document_processor import (
    process_document,
    process_document_incrementally,
    process_document_with_graph,
)

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


@router.put("/{document_id}/update")
async def update_document(
    document_id: UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing document with incremental processing
    Only reprocesses if content has changed (detected via hash comparison)

    Args:
        document_id: ID of document to update
        file: New document file (.md only)
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated user

    Returns:
        Update status with version information
    """
    # Validate file type
    if not file.filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Only Markdown (.md) files are allowed")

    # Check if document exists and belongs to user
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Save new file (overwrite existing)
    file_location = document.file_path
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    # Update document metadata
    document.filename = file.filename
    document.status = "processing"
    document.error_message = None
    db.commit()

    # Process incrementally in background
    async def process_incremental():
        """Async wrapper for incremental processing"""
        result = await process_document_incrementally(
            document_id=str(document_id),
            file_path=file_location,
            db=db,
        )
        return result

    background_tasks.add_task(asyncio.create_task, process_incremental())

    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "version": document.version,
        "message": "Document update initiated with incremental processing",
    }


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    force_full: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reprocess an existing document
    By default uses incremental processing, set force_full=True for complete reprocessing

    Args:
        document_id: ID of document to reprocess
        background_tasks: FastAPI background tasks
        force_full: If True, forces full reprocessing (ignores content hash)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Reprocessing status
    """
    # Check if document exists and belongs to user
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status == "processing":
        raise HTTPException(status_code=409, detail="Document is already being processed")

    # Update document status
    document.status = "processing"
    document.error_message = None

    if force_full:
        # Clear content hash to force full reprocessing
        document.content_hash = None

    db.commit()

    # Choose processing method
    if force_full:
        # Full reprocessing
        background_tasks.add_task(
            process_document,
            str(document_id),
            document.file_path,
            db
        )
        message = "Full document reprocessing initiated"
    else:
        # Incremental processing
        async def process_incremental():
            """Async wrapper for incremental processing"""
            result = await process_document_incrementally(
                document_id=str(document_id),
                file_path=document.file_path,
                db=db,
            )
            return result

        background_tasks.add_task(asyncio.create_task, process_incremental())
        message = "Incremental document reprocessing initiated"

    return {
        "id": document.id,
        "filename": document.filename,
        "status": document.status,
        "version": document.version,
        "force_full": force_full,
        "message": message,
    }


@router.get("/{document_id}/version-info")
def get_document_version_info(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get version tracking information for a document

    Args:
        document_id: ID of the document
        db: Database session
        current_user: Current authenticated user

    Returns:
        Document version information including hash and processing timestamps
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
        "version": document.version,
        "content_hash": document.content_hash,
        "last_processed_at": document.last_processed_at.isoformat() if document.last_processed_at else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "status": document.status,
    }
