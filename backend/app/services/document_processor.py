"""
Document processing service
Handles document parsing for Markdown (.md) files only
"""

import logging
from pathlib import Path
from typing import List, Tuple

from app.config import get_settings
from app.models.document import Document
from app.db.neo4j import get_neo4j_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors"""

    pass


class DocumentProcessor:
    """Document processor for parsing Markdown (.md) files only"""

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
    def parse_md(file_path: str) -> Tuple[str, List]:
        """
        Parse Markdown file and extract text content

        Args:
            file_path: Path to Markdown file

        Returns:
            Tuple of (full_text, elements)
        """
        try:
            logger.info(f"📄 Reading Markdown file: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()

            # For Markdown, we'll create a simple element structure
            # In a real implementation, you might want to parse the markdown structure
            elements = [{"type": "text", "text": full_text}]

            logger.info(f"✅ Successfully parsed Markdown: {len(elements)} elements extracted")
            return full_text, elements
        except Exception as e:
            logger.error(f"❌ Error parsing Markdown: {str(e)}")
            raise DocumentProcessingError(f"Failed to parse Markdown: {str(e)}")

    @staticmethod
    def process_document(file_path: str) -> Tuple[str, List]:
        """
        Process Markdown document

        Args:
            file_path: Path to document file

        Returns:
            Tuple of (full_text, elements)

        Raises:
            DocumentProcessingError: If file type not supported or parsing fails
        """
        file_ext = Path(file_path).suffix.lower().lstrip(".")

        logger.info(f"🔄 Processing document: {file_path} (type: {file_ext})")

        if file_ext == "md":
            return DocumentProcessor.parse_md(file_path)
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
    from app.services.llm_service import extract_entities_and_relationships  # Import here to avoid circular import
    
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
        session = get_neo4j_session()
        with session:
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
