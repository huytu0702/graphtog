"""
Document processing service with GraphRAG integration
Handles document parsing, chunking, entity extraction, and graph building
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.document import Document
from app.services.chunking import chunking_service
from app.services.community_detection import community_detection_service
from app.services.community_summarization import community_summarization_service
from app.services.embedding_service import embedding_service
from app.services.entity_resolution import entity_resolution_service
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


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash of document content

    Args:
        content: Document text content

    Returns:
        SHA256 hash as hexadecimal string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def detect_document_changes(
    document: Document,
    new_content: str,
) -> Dict[str, any]:
    """
    Detect if document content has changed by comparing hashes

    Args:
        document: Existing document record from database
        new_content: New document content to compare

    Returns:
        Dictionary with change detection results:
        - has_changed (bool): Whether content has changed
        - old_hash (str): Previous content hash
        - new_hash (str): New content hash
        - requires_reprocessing (bool): Whether full reprocessing is needed
    """
    new_hash = compute_content_hash(new_content)
    old_hash = document.content_hash

    has_changed = (old_hash is None) or (old_hash != new_hash)

    return {
        "has_changed": has_changed,
        "old_hash": old_hash,
        "new_hash": new_hash,
        "requires_reprocessing": has_changed,
        "current_version": document.version,
    }


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
        "embeddings_generated": 0,
        "entities_extracted": 0,
        "entities_merged": 0,
        "entities_resolved_with_llm": 0,
        "relationships_extracted": 0,
        "claims_extracted": 0,
        "communities_detected": 0,
        "communities_summarized": 0,
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

        # Step 5: Create TextUnit nodes in the knowledge graph
        logger.info("Step 5: Creating TextUnit nodes...")
        if update_callback:
            await update_callback("extraction", 40)

        chunk_data = []
        chunk_metadata: List[Dict[str, object]] = []
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
            chunk_metadata.append(
                {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "start_char": start_char,
                    "end_char": end_char,
                }
            )

        # Step 6: Generate and store embeddings with pgvector
        logger.info("Step 6: Generating Gemini embeddings for chunks...")
        if update_callback:
            await update_callback("embeddings", 45)

        try:
            embedding_stats = await embedding_service.generate_and_store_embeddings(
                db,
                document_id=document_id,
                chunks=chunk_metadata,
            )
            results["embeddings_generated"] = embedding_stats.get("embedded", 0)
            logger.info(
                "Stored %s embeddings (skipped %s)",
                embedding_stats.get("embedded", 0),
                embedding_stats.get("skipped", 0),
            )
        except Exception as embed_error:
            logger.error("Embedding storage failed: %s", embed_error)

        # Step 7: Extract entities AND relationships with GraphRAG gleaning (replaces old 7 and 8)
        logger.info("Step 7: Extracting entities and relationships with GraphRAG gleaning...")
        if update_callback:
            await update_callback("graph_extraction", 50)

        # Use gleaning-based extraction if enabled, otherwise fall back to old batch method
        if settings.ENABLE_GRAPHRAG_GLEANING:
            logger.info("Using GraphRAG gleaning-based extraction...")
            
            extraction_config = {
                "entity_types": settings.ENTITY_TYPES or None,
                "max_gleanings": settings.MAX_GLEANINGS,
            }

            all_extractions = []
            for chunk_text, chunk_id in chunk_data:
                extraction_result = await llm_service.extract_graph_with_gleaning(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    **extraction_config,
                )
                all_extractions.append(extraction_result)

                if extraction_result["status"] == "success":
                    results["entities_extracted"] += len(extraction_result["entities"])
                    results["relationships_extracted"] += len(extraction_result["relationships"])

                    # Create entity nodes
                    for entity in extraction_result["entities"]:
                        entity_id = graph_service.create_or_merge_entity(
                            name=entity.get("name", ""),
                            entity_type=entity.get("type", "OTHER"),
                            description=entity.get("description", ""),
                            confidence=entity.get("confidence", 0.8),
                        )
                        if entity_id:
                            graph_service.create_mention_relationship(
                                entity_id=entity_id,
                                textunit_id=chunk_id,
                            )

                    # Create relationship edges
                    for rel in extraction_result["relationships"]:
                        source_entity = graph_service.find_entity_by_name(rel["source"])
                        target_entity = graph_service.find_entity_by_name(rel["target"])

                        if source_entity and target_entity:
                            graph_service.create_relationship(
                                source_entity_id=source_entity["id"],
                                target_entity_id=target_entity["id"],
                                relationship_type=rel.get("type", "RELATED_TO"),
                                description=rel.get("description", ""),
                                confidence=rel.get("strength", 5) / 10.0,
                            )

            logger.info(
                f"Extracted {results['entities_extracted']} entities and "
                f"{results['relationships_extracted']} relationships with gleaning"
            )
        else:
            logger.info("Using traditional separate entity and relationship extraction...")
            
            # Legacy: separate extraction
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

            # Step 8: Extract relationships (legacy path)
            chunk_with_entities = [
                (chunk_text, all_entities_by_chunk.get(chunk_id, []), chunk_id)
                for chunk_text, chunk_id in chunk_data
            ]

            rel_results = await llm_service.batch_extract_relationships(chunk_with_entities)

            for result in rel_results:
                if result["status"] == "success":
                    results["relationships_extracted"] += len(result["relationships"])
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

        # Step 7.5: Description summarization (new gleaning enhancement)
        if settings.ENABLE_GRAPHRAG_GLEANING and settings.ENABLE_DESCRIPTION_SUMMARIZATION:
            logger.info("Step 7.5: Consolidating entity descriptions across chunks...")
            if update_callback:
                await update_callback("entity_consolidation", 55)

            try:
                # Get all entities from graph
                all_graph_entities = graph_service.get_all_entities_for_document(document_id)

                # Group by (name, type)
                entity_groups = {}
                for entity in all_graph_entities:
                    key = (entity["name"].upper(), entity["type"].upper())
                    if key not in entity_groups:
                        entity_groups[key] = []
                    entity_groups[key].append(entity)

                # Summarize descriptions for entities with multiple mentions
                for key, entities in entity_groups.items():
                    if len(entities) > 1:
                        descriptions = [e["description"] for e in entities if e.get("description")]
                        if len(descriptions) > 1:
                            summarized = await llm_service.summarize_entity_descriptions(
                                entity_name=entities[0]["name"],
                                descriptions=descriptions,
                                max_length=settings.DESCRIPTION_MAX_LENGTH,
                            )
                            # Update entity in graph with summarized description
                            graph_service.update_entity_description(
                                entity_id=entities[0]["id"],
                                description=summarized,
                            )
                            logger.info(f"Consolidated description for entity: {entities[0]['name']}")
                            
            except Exception as summarization_error:
                logger.warning(f"Description summarization failed (continuing anyway): {summarization_error}")

        elif settings.ENABLE_ENTITY_RESOLUTION:
            logger.info("Step 7.5: Performing entity resolution and deduplication...")
            if update_callback:
                await update_callback("entity_resolution", 65)

            try:
                # Find duplicate entity pairs
                duplicate_pairs = entity_resolution_service.find_duplicate_entity_pairs(
                    entity_type=None,  # Check all entity types
                    threshold=settings.ENTITY_SIMILARITY_THRESHOLD,
                )

                entities_merged = 0
                entities_resolved_with_llm = 0

                for entity1, entity2, similarity in duplicate_pairs:
                    should_merge = False
                    canonical_name = entity1["name"]  # Default to first entity

                    # High similarity - auto merge if above threshold
                    if similarity >= settings.AUTO_MERGE_CONFIDENCE_THRESHOLD:
                        should_merge = True
                        logger.info(
                            f"Auto-merging entities (similarity: {similarity}): "
                            f"'{entity1['name']}' <- '{entity2['name']}'"
                        )
                    # Medium similarity - use LLM resolution if enabled
                    elif settings.ENABLE_LLM_ENTITY_RESOLUTION and similarity >= settings.ENTITY_SIMILARITY_THRESHOLD:
                        logger.info(
                            f"Using LLM to resolve entities (similarity: {similarity}): "
                            f"'{entity1['name']}' vs '{entity2['name']}'"
                        )
                        llm_result = await entity_resolution_service.resolve_with_llm(entity1, entity2)

                        if llm_result["status"] == "success" and llm_result.get("are_same", False):
                            should_merge = True
                            canonical_name = llm_result.get("suggested_canonical_name", entity1["name"])
                            entities_resolved_with_llm += 1
                            logger.info(
                                f"LLM resolution: MERGE (confidence: {llm_result.get('confidence')}). "
                                f"Reason: {llm_result.get('reasoning', 'N/A')}"
                            )
                        else:
                            logger.info(
                                f"LLM resolution: KEEP SEPARATE (confidence: {llm_result.get('confidence')})"
                            )

                    # Perform merge if decided
                    if should_merge:
                        # Choose primary entity (one with higher mention count)
                        if entity1.get("mention_count", 1) >= entity2.get("mention_count", 1):
                            primary_id = entity1["id"]
                            duplicate_id = entity2["id"]
                        else:
                            primary_id = entity2["id"]
                            duplicate_id = entity1["id"]

                        merge_result = entity_resolution_service.merge_entities(
                            primary_entity_id=primary_id,
                            duplicate_entity_ids=[duplicate_id],
                            canonical_name=canonical_name,
                        )

                        if merge_result["status"] == "success":
                            entities_merged += merge_result["merged_count"]

                logger.info(
                    f"✅ Entity resolution complete: {entities_merged} entities merged, "
                    f"{entities_resolved_with_llm} resolved with LLM"
                )
                results["entities_merged"] = entities_merged
                results["entities_resolved_with_llm"] = entities_resolved_with_llm

            except Exception as resolution_error:
                logger.warning(f"Entity resolution failed (continuing anyway): {resolution_error}")
                results["entities_merged"] = 0
                results["entities_resolved_with_llm"] = 0
        else:
            logger.info("Step 7.5: Entity resolution disabled (skipping)")

        # Step 8.5: Extract claims from chunks with entities
        logger.info("Step 8.5: Extracting claims from chunks...")
        if update_callback:
            await update_callback("claims_extraction", 72)

        claims_results = await llm_service.batch_extract_claims(chunk_with_entities)

        for result in claims_results:
            if result["status"] == "success":
                chunk_id = result["chunk_id"]
                claims = result.get("claims", [])

                for claim in claims:
                    # Create claim node
                    claim_id = graph_service.create_claim_node(
                        subject_entity_name=claim.get("subject", ""),
                        object_entity_name=claim.get("object", ""),
                        claim_type=claim.get("claim_type", "UNKNOWN"),
                        status=claim.get("status", "SUSPECTED"),
                        description=claim.get("description", ""),
                        start_date=claim.get("start_date"),
                        end_date=claim.get("end_date"),
                        source_text=claim.get("source_text", ""),
                    )

                    if claim_id:
                        # Link claim to entities
                        graph_service.link_claim_to_entities(
                            claim_id=claim_id,
                            subject_entity_name=claim.get("subject", ""),
                            object_entity_name=claim.get("object"),
                        )

                        # Link claim to text unit
                        graph_service.link_claim_to_textunit(
                            claim_id=claim_id,
                            textunit_id=chunk_id,
                        )

                        results["claims_extracted"] += 1

        logger.info(f"Extracted {results['claims_extracted']} claims")

        # Step 9: Community detection using Leiden algorithm
        logger.info("Step 9: Detecting communities with Leiden algorithm...")
        if update_callback:
            await update_callback("community_detection", 75)

        # Initialize and run community detection
        community_results = community_detection_service.detect_communities(
            seed=42,
            include_intermediate_communities=True,
            tolerance=0.0001,
            max_iterations=10,
        )
        
        if community_results["status"] == "success":
            num_communities = community_results.get("num_communities", 0)
            logger.info(f"✅ Detected {num_communities} communities")
            results["communities_detected"] = num_communities
        else:
            logger.warning(f"⚠️ Community detection had issues: {community_results.get('message', 'Unknown')}")
            results["communities_detected"] = 0

        # Step 10: Generate community summaries
        logger.info("Step 10: Generating community summaries...")
        if update_callback:
            await update_callback("summarization", 85)

        # Generate summaries for all detected communities
        summary_results = community_summarization_service.summarize_all_communities()
        if summary_results["status"] == "success":
            num_summarized = summary_results.get("num_communities_summarized", 0)
            logger.info(f"✅ Generated {num_summarized} community summaries")
            results["communities_summarized"] = num_summarized
        else:
            logger.warning(f"⚠️ Community summarization had issues: {summary_results.get('message', 'Unknown')}")
            results["communities_summarized"] = 0

        # Step 11: Update document status
        logger.info("Step 11: Finalizing processing...")
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


async def process_document_incrementally(
    document_id: str,
    file_path: str,
    db: Session,
    update_callback: Optional[callable] = None,
) -> Dict[str, any]:
    """
    Process document incrementally - only reprocess if content has changed
    This is more efficient for document updates

    Args:
        document_id: Document ID
        file_path: Path to document file
        db: Database session
        update_callback: Optional callback for progress updates

    Returns:
        Processing results dictionary with incremental_update flag
    """
    results = {
        "document_id": document_id,
        "status": "error",
        "incremental_update": False,
        "content_changed": False,
        "version": 1,
        "error": None,
    }

    try:
        # Get existing document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            results["error"] = f"Document with ID {document_id} not found"
            logger.error(results["error"])
            return results

        # Step 1: Parse new document content
        logger.info(f"Step 1: Parsing document {document_id} for change detection...")
        if update_callback:
            await update_callback("parsing", 5)

        full_text = DocumentProcessor.process_document(file_path)
        if not full_text:
            results["error"] = "Document is empty"
            logger.error(results["error"])
            return results

        # Step 2: Detect changes
        logger.info("Step 2: Detecting document changes...")
        if update_callback:
            await update_callback("change_detection", 10)

        change_info = detect_document_changes(document, full_text)
        results["content_changed"] = change_info["has_changed"]
        results["version"] = change_info["current_version"]

        if not change_info["has_changed"]:
            logger.info(f"✅ Document {document_id} content unchanged, skipping reprocessing")
            results["status"] = "success"
            results["message"] = "No changes detected, document not reprocessed"
            return results

        logger.info(
            f"🔄 Document {document_id} content changed "
            f"(old hash: {change_info['old_hash'][:8] if change_info['old_hash'] else 'none'}..., "
            f"new hash: {change_info['new_hash'][:8]}...)"
        )

        # Step 3: Mark document as processing and increment version
        document.status = "processing"
        document.version += 1
        document.content_hash = change_info["new_hash"]
        db.commit()

        results["incremental_update"] = True
        results["version"] = document.version

        # Step 4: Get affected communities before deletion
        logger.info("Step 3: Identifying affected communities...")
        if update_callback:
            await update_callback("analyzing_impact", 15)

        affected_communities = graph_service.get_affected_communities_for_document(
            document_id=str(document_id)
        )
        logger.info(f"Found {len(affected_communities)} affected communities")

        # Step 5: Delete old graph data for this document
        logger.info("Step 4: Cleaning up old graph data...")
        if update_callback:
            await update_callback("cleanup", 20)

        cleanup_result = graph_service.delete_document_graph_data(
            document_id=str(document_id)
        )
        logger.info(
            f"Cleaned up: {cleanup_result.get('textunits_deleted', 0)} text units, "
            f"{cleanup_result.get('entities_affected', 0)} entities affected"
        )

        # Step 6: Process document with full pipeline (reusing existing function)
        logger.info("Step 5: Reprocessing document with updated content...")
        if update_callback:
            await update_callback("reprocessing", 25)

        # Call the full processing pipeline
        processing_results = await process_document_with_graph(
            document_id=document_id,
            file_path=file_path,
            db=db,
            update_callback=update_callback,
        )

        # Step 7: Incremental community detection (only affected communities)
        if affected_communities and len(affected_communities) > 0:
            logger.info("Step 6: Running incremental community detection...")
            if update_callback:
                await update_callback("incremental_community_detection", 90)

            community_results = community_detection_service.detect_communities_incrementally(
                affected_entity_ids=affected_communities.get("affected_entities", []),
                seed=42,
            )

            if community_results["status"] == "success":
                logger.info(
                    f"✅ Incremental community detection complete: "
                    f"{community_results.get('communities_recomputed', 0)} communities recomputed"
                )
                processing_results["communities_recomputed"] = community_results.get(
                    "communities_recomputed", 0
                )
        else:
            # Run full community detection if no previous communities
            logger.info("Running full community detection (no previous communities)...")
            processing_results["communities_recomputed"] = 0

        # Step 8: Update document metadata
        logger.info("Step 7: Updating document metadata...")
        document.last_processed_at = datetime.utcnow()
        db.commit()

        # Merge results
        results.update(processing_results)
        results["incremental_update"] = True
        results["status"] = "success"
        results["message"] = f"Document updated successfully to version {document.version}"

        logger.info(
            f"✅ Incremental processing complete for document {document_id} "
            f"(version {document.version})"
        )

        if update_callback:
            await update_callback("completed", 100)

        return results

    except Exception as e:
        logger.error(f"❌ Error in incremental processing for document {document_id}: {str(e)}")
        results["error"] = str(e)

        # Update document status to error
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                document.error_message = str(e)
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
