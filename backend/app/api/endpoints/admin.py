"""
Admin endpoints for testing and debugging
"""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

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
