"""
Document processing service with GraphRAG integration
Handles document parsing, chunking, entity extraction, and graph building
"""

import asyncio
import hashlib
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.document import Document
from app.services.chunking import chunking_service
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors"""

    pass


class DocumentProcessor:
    """Document processor for parsing and processing Markdown files with GraphRAG"""

    SUPPORTED_FORMATS = {"md"}

    @staticmethod
    def validate_file_type(file_path: str) -> bool:
        """
        Validate if file type is supported

        Args:
            file_path: Path to the file

        Returns:
            True if supported (only .md files), False otherwise
        """
        file_ext = Path(file_path).suffix.lower().lstrip(".")
        return file_ext in DocumentProcessor.SUPPORTED_FORMATS

    @staticmethod
    def parse_md(file_path: str) -> str:
        """
        Parse Markdown file and extract text content

        Args:
            file_path: Path to Markdown file

        Returns:
            Full text content
        """
        try:
            logger.info(f"📄 Reading Markdown file: {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                full_text = f.read()

            logger.info(f"✅ Successfully parsed Markdown: {len(full_text)} characters")
            return full_text

        except Exception as e:
            logger.error(f"❌ Error parsing Markdown: {str(e)}")
            raise DocumentProcessingError(f"Failed to parse Markdown: {str(e)}")

    @staticmethod
    def process_document(file_path: str) -> str:
        """
        Process Markdown document

        Args:
            file_path: Path to document file

        Returns:
            Full text content

        Raises:
            DocumentProcessingError: If file type not supported or parsing fails
        """
        file_ext = Path(file_path).suffix.lower().lstrip(".")

        logger.info(f"🔄 Processing document: {file_path} (type: {file_ext})")

        if file_ext == "md":
            return DocumentProcessor.parse_md(file_path)
        else:
            raise DocumentProcessingError(f"Unsupported file format: {file_ext}")


async def process_document_with_graph(
    document_id: str,
    file_path: str,
    db: Session,
    update_callback: Optional[callable] = None,
) -> Dict[str, any]:
    """
    Process document with full GraphRAG pipeline

    Args:
        document_id: Document ID
        file_path: Path to document file
        db: Database session
        update_callback: Optional callback for progress updates

    Returns:
        Processing results dictionary
    """
    results = {
        "document_id": document_id,
        "status": "error",
        "chunks_created": 0,
        "entities_extracted": 0,
        "relationships_extracted": 0,
        "error": None,
    }

    try:
        # Update document status to processing
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            results["error"] = f"Document with ID {document_id} not found"
            logger.error(results["error"])
            return results

        document.status = "processing"
        document.processing_progress = 0
        db.commit()

        # Step 1: Parse document
        logger.info(f"Step 1: Parsing document {document_id}...")
        if update_callback:
            await update_callback("parsing", 10)

        full_text = DocumentProcessor.process_document(file_path)
        if not full_text:
            results["error"] = "Document is empty"
            logger.error(results["error"])
            return results

        # Step 2: Initialize graph schema
        logger.info("Step 2: Initializing graph schema...")
        if update_callback:
            await update_callback("schema_init", 15)

        graph_service.init_schema()

        # Step 3: Create document node in graph
        logger.info(f"Step 3: Creating document node...")
        if update_callback:
            await update_callback("doc_node_creation", 20)

        graph_service.create_document_node(
            document_id=document_id,
            document_name=document.filename,
            file_path=file_path,
        )

        # Step 4: Chunk document
        logger.info("Step 4: Chunking document...")
        if update_callback:
            await update_callback("chunking", 25)

        chunks = chunking_service.create_chunks(full_text)
        results["chunks_created"] = len(chunks)
        logger.info(f"Created {len(chunks)} chunks")

        # Step 5: Create TextUnit nodes and extract entities
        logger.info("Step 5: Processing chunks for entity extraction...")
        if update_callback:
            await update_callback("extraction", 40)

        chunk_data = []
        for i, (chunk_text, start_char, end_char) in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"

            # Create TextUnit node
            graph_service.create_textunit_node(
                textunit_id=chunk_id,
                document_id=document_id,
                text=chunk_text,
                start_char=start_char,
                end_char=end_char,
            )

            chunk_data.append((chunk_text, chunk_id))

        # Step 6: Batch extract entities from all chunks
        logger.info("Step 6: Extracting entities from chunks...")
        entity_results = await llm_service.batch_extract_entities(chunk_data)

        all_entities_by_chunk = {}
        for result in entity_results:
            if result["status"] == "success":
                chunk_id = result["chunk_id"]
                all_entities_by_chunk[chunk_id] = result["entities"]
                results["entities_extracted"] += len(result["entities"])

                # Create entity nodes in graph
                for entity in result["entities"]:
                    entity_id = graph_service.create_or_merge_entity(
                        name=entity.get("name", ""),
                        entity_type=entity.get("type", "OTHER"),
                        description=entity.get("description", ""),
                        confidence=entity.get("confidence", 0.8),
                    )

                    if entity_id:
                        # Link entity to text unit
                        graph_service.create_mention_relationship(
                            entity_id=entity_id,
                            textunit_id=chunk_id,
                        )

        # Step 7: Extract relationships
        logger.info("Step 7: Extracting relationships...")
        if update_callback:
            await update_callback("relationship_extraction", 70)

        chunk_with_entities = [
            (chunk_text, all_entities_by_chunk.get(chunk_id, []), chunk_id)
            for chunk_text, chunk_id in chunk_data
        ]

        rel_results = await llm_service.batch_extract_relationships(chunk_with_entities)

        for result in rel_results:
            if result["status"] == "success":
                for relationship in result["relationships"]:
                    source_name = relationship.get("source", "")
                    target_name = relationship.get("target", "")

                    # Find entity IDs
                    source_entity = graph_service.find_entity_by_name(source_name)
                    target_entity = graph_service.find_entity_by_name(target_name)

                    if source_entity and target_entity:
                        rel_type = relationship.get("type", "RELATED_TO")
                        graph_service.create_relationship(
                            source_entity_id=source_entity["id"],
                            target_entity_id=target_entity["id"],
                            relationship_type=rel_type,
                            description=relationship.get("description", ""),
                            confidence=relationship.get("confidence", 0.8),
                        )
                        results["relationships_extracted"] += 1

        # Step 8: Update document status
        logger.info("Step 8: Finalizing processing...")
        if update_callback:
            await update_callback("finalization", 95)

        document.status = "completed"
        document.processing_progress = 100
        db.commit()

        results["status"] = "success"
        logger.info(f"✅ Document {document_id} processed successfully")

        if update_callback:
            await update_callback("completed", 100)

        return results

    except Exception as e:
        logger.error(f"❌ Error processing document {document_id}: {str(e)}")
        results["error"] = str(e)

        # Update document status to error
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "error"
                document.processing_progress = 0
                db.commit()
        except Exception as db_error:
            logger.error(f"Error updating document status: {db_error}")

        return results


def process_document(document_id: str, file_path: str, db: Session):
    """
    Synchronous wrapper for process_document_with_graph to work with BackgroundTasks
    """
    import asyncio
    
    # Create a new event loop if none exists
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No event loop running, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            process_document_with_graph(document_id, file_path, db)
        )
        loop.close()
        return result
    else:
        # Event loop already running, run in executor
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                process_document_with_graph(document_id, file_path, db)
            )
            result = future.result()
        return result
