"""
Admin endpoints for testing and debugging
"""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from app.schemas.entity_resolution import (
    AddAliasRequest,
    AddAliasResponse,
    FindDuplicatesRequest,
    FindDuplicatesResponse,
    FindSimilarEntitiesRequest,
    FindSimilarEntitiesResponse,
    GetAliasesRequest,
    GetAliasesResponse,
    LLMResolutionRequest,
    LLMResolutionResponse,
    MergeEntitiesRequest,
    MergeEntitiesResponse,
    DuplicatePair,
    EntityInfo,
    SimilarEntityResponse,
)
from app.services.entity_resolution import entity_resolution_service
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


@router.get("/admin/graph/stats")
async def get_detailed_graph_stats() -> Dict:
    """
    Get detailed graph statistics

    Returns:
        Detailed statistics about the knowledge graph
    """
    try:
        stats = graph_service.get_graph_statistics()

        return {
            "status": "success",
            "statistics": {
                "documents": stats.get("documents", 0),
                "text_units": stats.get("textunits", 0),
                "entities": stats.get("entities", 0),
                "relationships": stats.get("relationships", 0),
                "timestamp": None,  # Would add timestamp if needed
            },
        }

    except Exception as e:
        logger.error(f"Error getting graph statistics: {e}")
        raise HTTPException(status_code=500, detail="Error getting statistics")


@router.post("/admin/test-entity-extraction")
async def test_entity_extraction(request: dict) -> Dict:
    """
    Test entity extraction on sample text

    Args:
        request: Dict with "text" key

    Returns:
        Extracted entities
    """
    try:
        text = request.get("text", "").strip()

        if not text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        if len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long (max 5000 chars)")

        logger.info("Testing entity extraction...")
        result = llm_service.extract_entities(text, "test_chunk")

        return {
            "status": "success",
            "test_result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity extraction test error: {e}")
        raise HTTPException(status_code=500, detail="Test failed")


@router.post("/admin/test-relationship-extraction")
async def test_relationship_extraction(request: dict) -> Dict:
    """
    Test relationship extraction

    Args:
        request: Dict with "text" and "entities" keys

    Returns:
        Extracted relationships
    """
    try:
        text = request.get("text", "").strip()
        entities = request.get("entities", [])

        if not text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        if not entities:
            raise HTTPException(status_code=400, detail="Entities cannot be empty")

        logger.info("Testing relationship extraction...")
        result = llm_service.extract_relationships(text, entities, "test_chunk")

        return {
            "status": "success",
            "test_result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Relationship extraction test error: {e}")
        raise HTTPException(status_code=500, detail="Test failed")


@router.post("/admin/test-query-classification")
async def test_query_classification(request: dict) -> Dict:
    """
    Test query classification

    Args:
        request: Dict with "query" key

    Returns:
        Query classification result
    """
    try:
        query = request.get("query", "").strip()

        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        logger.info(f"Testing query classification: {query}")
        result = llm_service.classify_query(query)

        return {
            "status": "success",
            "classification": result.get("classification", {}),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query classification test error: {e}")
        raise HTTPException(status_code=500, detail="Test failed")


@router.post("/admin/test-answer-generation")
async def test_answer_generation(request: dict) -> Dict:
    """
    Test answer generation

    Args:
        request: Dict with "query", "context", and optional "citations"

    Returns:
        Generated answer
    """
    try:
        query = request.get("query", "").strip()
        context = request.get("context", "").strip()
        citations = request.get("citations", [])

        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        if not context:
            raise HTTPException(status_code=400, detail="Context cannot be empty")

        logger.info(f"Testing answer generation for: {query}")
        result = llm_service.generate_answer(query, context, citations)

        return {
            "status": "success",
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Answer generation test error: {e}")
        raise HTTPException(status_code=500, detail="Test failed")


@router.get("/admin/health")
async def admin_health_check() -> Dict:
    """
    Admin health check with component status

    Returns:
        Health status of all components
    """
    try:
        # Check graph service
        stats = graph_service.get_graph_statistics()
        graph_healthy = stats is not None and len(stats) > 0

        return {
            "status": "healthy" if graph_healthy else "degraded",
            "components": {
                "graph_service": "healthy" if graph_healthy else "unhealthy",
                "llm_service": "ready",  # LLM service doesn't maintain state
                "timestamp": None,
            },
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "components": {
                "graph_service": "unhealthy",
                "llm_service": "unknown",
            },
        }


# ==================== Entity Resolution Endpoints ====================


@router.post("/entity-resolution/find-similar", response_model=FindSimilarEntitiesResponse)
async def find_similar_entities(request: FindSimilarEntitiesRequest):
    """
    Find similar entities using fuzzy string matching

    This endpoint uses the Levenshtein distance algorithm to find entities
    with similar names that might be duplicates.

    Args:
        request: Search parameters including entity name, type, and threshold

    Returns:
        List of similar entities with similarity scores
    """
    try:
        similar_entities = entity_resolution_service.find_similar_entities(
            entity_name=request.entity_name,
            entity_type=request.entity_type,
            threshold=request.threshold,
        )

        # Convert to response models
        similar_responses = [
            SimilarEntityResponse(**entity) for entity in similar_entities
        ]

        threshold_used = request.threshold if request.threshold is not None else 0.85

        return FindSimilarEntitiesResponse(
            status="success",
            query={
                "entity_name": request.entity_name,
                "entity_type": request.entity_type,
                "threshold": str(threshold_used),
            },
            similar_entities=similar_responses,
            count=len(similar_responses),
        )

    except Exception as e:
        logger.error(f"Error finding similar entities: {e}")
        raise HTTPException(status_code=500, detail=f"Error finding similar entities: {str(e)}")


@router.post("/entity-resolution/find-duplicates", response_model=FindDuplicatesResponse)
async def find_duplicate_entities(request: FindDuplicatesRequest):
    """
    Find all potential duplicate entity pairs in the graph

    Scans the entire graph (or filtered by entity type) to find pairs of
    entities with similar names that might be duplicates.

    Args:
        request: Filter parameters (entity type, threshold)

    Returns:
        List of duplicate pairs with similarity scores
    """
    try:
        duplicate_pairs = entity_resolution_service.find_duplicate_entity_pairs(
            entity_type=request.entity_type,
            threshold=request.threshold,
        )

        # Convert to response models
        duplicate_responses = [
            DuplicatePair(
                entity1=EntityInfo(**pair[0]),
                entity2=EntityInfo(**pair[1]),
                similarity=pair[2],
            )
            for pair in duplicate_pairs
        ]

        threshold_used = request.threshold or entity_resolution_service.similarity_threshold

        return FindDuplicatesResponse(
            status="success",
            duplicate_pairs=duplicate_responses,
            count=len(duplicate_responses),
            threshold=threshold_used,
        )

    except Exception as e:
        logger.error(f"Error finding duplicate entities: {e}")
        raise HTTPException(status_code=500, detail=f"Error finding duplicates: {str(e)}")


@router.post("/entity-resolution/llm-resolve", response_model=LLMResolutionResponse)
async def resolve_entities_with_llm(request: LLMResolutionRequest):
    """
    Use LLM to determine if two entities are the same

    For ambiguous cases where fuzzy matching is inconclusive, this endpoint
    uses an LLM to analyze entity names and descriptions to make an intelligent
    determination about whether they refer to the same real-world entity.

    Args:
        request: Entity IDs to compare

    Returns:
        Resolution result with confidence score and reasoning
    """
    try:
        # Get entity details from graph
        session = graph_service.get_session()

        query = """
        MATCH (e:Entity {id: $entity_id})
        RETURN e.id as id, e.name as name, e.type as type,
               e.description as description, e.confidence as confidence,
               e.mention_count as mention_count
        """

        result1 = session.run(query, entity_id=request.entity1_id)
        record1 = result1.single()
        if not record1:
            raise HTTPException(status_code=404, detail=f"Entity {request.entity1_id} not found")

        result2 = session.run(query, entity_id=request.entity2_id)
        record2 = result2.single()
        if not record2:
            raise HTTPException(status_code=404, detail=f"Entity {request.entity2_id} not found")

        entity1 = dict(record1)
        entity2 = dict(record2)

        # Call LLM resolution
        resolution_result = await entity_resolution_service.resolve_with_llm(entity1, entity2)

        return LLMResolutionResponse(
            status=resolution_result["status"],
            are_same=resolution_result.get("are_same", False),
            confidence=resolution_result.get("confidence", 0.0),
            reasoning=resolution_result.get("reasoning", ""),
            suggested_canonical_name=resolution_result.get("suggested_canonical_name"),
            entity1=EntityInfo(**entity1),
            entity2=EntityInfo(**entity2),
            error=resolution_result.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in LLM resolution: {e}")
        raise HTTPException(status_code=500, detail=f"LLM resolution failed: {str(e)}")


@router.post("/entity-resolution/merge", response_model=MergeEntitiesResponse)
async def merge_duplicate_entities(request: MergeEntitiesRequest):
    """
    Merge duplicate entities into a primary entity

    This operation will:
    1. Aggregate mention counts from all entities
    2. Transfer all relationships to the primary entity
    3. Transfer all text unit mentions to the primary entity
    4. Store duplicate names as aliases
    5. Delete the duplicate entities

    This operation is irreversible, so use with caution!

    Args:
        request: Primary entity ID, duplicate entity IDs, and optional canonical name

    Returns:
        Merge result with count of merged entities
    """
    try:
        result = entity_resolution_service.merge_entities(
            primary_entity_id=request.primary_entity_id,
            duplicate_entity_ids=request.duplicate_entity_ids,
            canonical_name=request.canonical_name,
        )

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result.get("error", "Merge failed"))

        return MergeEntitiesResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging entities: {e}")
        raise HTTPException(status_code=500, detail=f"Entity merge failed: {str(e)}")


@router.post("/entity-resolution/add-alias", response_model=AddAliasResponse)
async def add_entity_alias(request: AddAliasRequest):
    """
    Add an alias to an existing entity

    Use this to manually track alternative names for an entity
    (e.g., "Microsoft" -> "MS", "MSFT", etc.)

    Args:
        request: Entity ID and alias to add

    Returns:
        Updated list of all aliases for the entity
    """
    try:
        success = entity_resolution_service.add_entity_alias(
            entity_id=request.entity_id,
            alias=request.alias,
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to add alias")

        # Get all aliases
        all_aliases = entity_resolution_service.get_entity_aliases(request.entity_id)

        return AddAliasResponse(
            status="success",
            entity_id=request.entity_id,
            alias=request.alias,
            all_aliases=all_aliases,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding alias: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add alias: {str(e)}")


@router.get("/entity-resolution/aliases/{entity_id}", response_model=GetAliasesResponse)
async def get_entity_aliases(entity_id: str):
    """
    Get all known aliases for an entity

    Args:
        entity_id: Entity ID

    Returns:
        Canonical name and list of aliases
    """
    try:
        # Get entity info
        session = graph_service.get_session()
        result = session.run(
            """
            MATCH (e:Entity {id: $entity_id})
            RETURN e.name as canonical_name, e.aliases as aliases
            """,
            entity_id=entity_id
        )

        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        canonical_name = record.get("canonical_name", "")
        aliases = record.get("aliases", []) or []

        return GetAliasesResponse(
            status="success",
            entity_id=entity_id,
            canonical_name=canonical_name,
            aliases=aliases,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting aliases: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get aliases: {str(e)}")
