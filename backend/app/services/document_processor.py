"""
Document processing service
Handles document parsing using Unstructured library with PaddleOCR
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

from unstructured.partition.auto import partition
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.docx import partition_docx
from unstructured.partition.text import partition_text
from unstructured.partition.pptx import partition_pptx

from backend.app.config import get_settings
from backend.app.models.document import Document
from backend.app.db.neo4j import get_neo4j_driver
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors"""

    pass


class DocumentProcessor:
    """Document processor for parsing various file formats"""

    SUPPORTED_FORMATS = {"pdf", "docx", "txt", "pptx", "xlsx"}

    @staticmethod
    def validate_file_type(file_path: str) -> bool:
        """
        Validate if file type is supported

        Args:
            file_path: Path to the file

        Returns:
            True if supported, False otherwise
        """
        file_ext = Path(file_path).suffix.lower().lstrip(".")
        return file_ext in DocumentProcessor.SUPPORTED_FORMATS

    @staticmethod
    def parse_pdf(file_path: str, languages: Optional[List[str]] = None) -> Tuple[str, List]:
        """
        Parse PDF file using Unstructured with PaddleOCR

        Args:
            file_path: Path to PDF file
            languages: Language codes for PaddleOCR (e.g., ['vi', 'en'])

        Returns:
            Tuple of (full_text, elements)
        """
        try:
            if languages is None:
                languages = ["vi", "en"]

            logger.info(f"📄 Parsing PDF: {file_path} with languages {languages}")

            # Use PaddleOCR through Unstructured
            elements = partition_pdf(
                filename=file_path,
                languages=languages,
            )

            # Extract text from elements
            full_text = "\n".join([str(el) for el in elements])
            logger.info(f"✅ Successfully parsed PDF: {len(elements)} elements extracted")

            return full_text, elements
        except Exception as e:
            logger.error(f"❌ Error parsing PDF: {str(e)}")
            raise DocumentProcessingError(f"Failed to parse PDF: {str(e)}")

    @staticmethod
    def parse_docx(file_path: str) -> Tuple[str, List]:
        """
        Parse DOCX file

        Args:
            file_path: Path to DOCX file

        Returns:
            Tuple of (full_text, elements)
        """
        try:
            logger.info(f"📄 Parsing DOCX: {file_path}")

            elements = partition_docx(filename=file_path)
            full_text = "\n".join([str(el) for el in elements])

            logger.info(f"✅ Successfully parsed DOCX: {len(elements)} elements extracted")
            return full_text, elements
        except Exception as e:
            logger.error(f"❌ Error parsing DOCX: {str(e)}")
            raise DocumentProcessingError(f"Failed to parse DOCX: {str(e)}")

    @staticmethod
    def parse_txt(file_path: str) -> Tuple[str, List]:
        """
        Parse TXT file

        Args:
            file_path: Path to TXT file

        Returns:
            Tuple of (full_text, elements)
        """
        try:
            logger.info(f"📄 Parsing TXT: {file_path}")

            elements = partition_text(filename=file_path)
            full_text = "\n".join([str(el) for el in elements])

            logger.info(f"✅ Successfully parsed TXT: {len(elements)} elements extracted")
            return full_text, elements
        except Exception as e:
            logger.error(f"❌ Error parsing TXT: {str(e)}")
            raise DocumentProcessingError(f"Failed to parse TXT: {str(e)}")

    @staticmethod
    def parse_pptx(file_path: str) -> Tuple[str, List]:
        """
        Parse PPTX file

        Args:
            file_path: Path to PPTX file

        Returns:
            Tuple of (full_text, elements)
        """
        try:
            logger.info(f"📄 Parsing PPTX: {file_path}")

            elements = partition_pptx(filename=file_path)
            full_text = "\n".join([str(el) for el in elements])

            logger.info(f"✅ Successfully parsed PPTX: {len(elements)} elements extracted")
            return full_text, elements
        except Exception as e:
            logger.error(f"❌ Error parsing PPTX: {str(e)}")
            raise DocumentProcessingError(f"Failed to parse PPTX: {str(e)}")

    @staticmethod
    def process_document(file_path: str) -> Tuple[str, List]:
        """
        Process document based on file type
        Auto-detects file format and calls appropriate parser

        Args:
            file_path: Path to document file

        Returns:
            Tuple of (full_text, elements)

        Raises:
            DocumentProcessingError: If file type not supported or parsing fails
        """
        file_ext = Path(file_path).suffix.lower().lstrip(".")

        logger.info(f"🔄 Processing document: {file_path} (type: {file_ext})")

        if file_ext == "pdf":
            return DocumentProcessor.parse_pdf(file_path)
        elif file_ext == "docx":
            return DocumentProcessor.parse_docx(file_path)
        elif file_ext == "txt":
            return DocumentProcessor.parse_txt(file_path)
        elif file_ext == "pptx":
            return DocumentProcessor.parse_pptx(file_path)
        else:
            raise DocumentProcessingError(f"Unsupported file format: {file_ext}")

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks

        Args:
            text: Full text to chunk
            chunk_size: Size of each chunk
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap

        logger.info(f"📊 Text chunked into {len(chunks)} chunks")
        return chunks


def process_document(document_id: int, file_path: str, db: Session):
    """
    Process document in background task
    This function is designed to run as a background task
    """
    from backend.app.services.llm_service import extract_entities_and_relationships  # Import here to avoid circular import
    
    try:
        # Update document status to processing
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document with ID {document_id} not found")
            return
        
        document.status = "processing"
        db.commit()
        
        # Process the document based on its type
        full_text, elements = DocumentProcessor.process_document(file_path)
        
        # Chunk the text
        chunks = DocumentProcessor.chunk_text(full_text)
        
        # Connect to Neo4j to store the document data
        driver = get_neo4j_driver()
        with driver.session() as session:
            # Create document node in Neo4j
            session.run(
                """
                MERGE (d:Document {id: $document_id})
                SET d.filename = $filename, d.status = $status, d.created_at = datetime()
                """,
                document_id=str(document_id),
                filename=document.filename,
                status="processed"
            )
            
            # Store text chunks as sentences in Neo4j
            for i, chunk in enumerate(chunks):
                session.run(
                    """
                    MATCH (d:Document {id: $document_id})
                    CREATE (d)-[:CONTAINS]->(s:Sentence {
                        id: $sentence_id,
                        text: $text,
                        chunk_index: $chunk_index
                    })
                    """,
                    document_id=str(document_id),
                    sentence_id=f"{document_id}_chunk_{i}",
                    text=chunk,
                    chunk_index=i
                )
            
            # Extract entities and relationships using LLM
            # This is a simplified version - in a real implementation, you'd want to batch this
            for i, chunk in enumerate(chunks):
                entities_and_relations = extract_entities_and_relationships(chunk)
                
                # Create entity nodes and relationships in Neo4j
                for entity in entities_and_relations.get("entities", []):
                    session.run(
                        """
                        MERGE (e:Entity {name: $name, type: $type})
                        SET e.description = $description
                        """,
                        name=entity["name"],
                        type=entity["type"],
                        description=entity.get("description", "")
                    )
                
                for relation in entities_and_relations.get("relationships", []):
                    session.run(
                        """
                        MATCH (e1:Entity {name: $source})
                        MATCH (e2:Entity {name: $target})
                        MERGE (e1)-[r:RELATED {type: $relation_type}]->(e2)
                        SET r.description = $description
                        """,
                        source=relation["source"],
                        target=relation["target"],
                        relation_type=relation["type"],
                        description=relation.get("description", "")
                    )
        
        # Update document status to completed
        document.status = "completed"
        db.commit()
        
        logger.info(f"✅ Document {document_id} processed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error processing document {document_id}: {str(e)}")
        # Update document status to error
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "error"
            document.error_message = str(e)
            db.commit()
