"""
Tree of Graphs (ToG) API endpoints for multi-hop reasoning queries
"""

import time
import logging
from typing import Dict, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.models.user import User
from app.models.query import Query
from app.services.auth import get_current_user
from app.services.tog_service import ToGService, ToGConfig
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service
from app.services.tog_visualization import ToGVisualizationService
from app.services.tog_analytics import ToGAnalyticsService
from app.schemas.tog import (
    ToGQueryRequest,
    ToGQueryResponse,
    ToGExplainRequest,
    ToGExplainResponse,
    ToGConfigRequest,
    ToGConfigResponse,
    ToGConfigSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tog", tags=["tog"])

# Initialize ToG services
tog_service = ToGService(graph_service, llm_service)
tog_visualization = ToGVisualizationService()
tog_analytics = ToGAnalyticsService()


@router.post("/query", response_model=ToGQueryResponse)
async def tog_query(
    request: ToGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToGQueryResponse:
    """
    Process a query using Tree of Graphs (ToG) reasoning.

    Performs iterative graph exploration with LLM-guided pruning to answer complex questions
    requiring multi-hop reasoning through the knowledge graph.

    Args:
        request: ToG query request with question and configuration
        current_user: Current authenticated user
        db: Database session

    Returns:
        ToG query response with answer and reasoning path
    """
    start_time = time.time()

    try:
        logger.info(f"ToG query from user {current_user.id}: {request.question}")

        # Convert schema config to service config
        config = ToGConfig(
            search_width=request.config.search_width,
            search_depth=request.config.search_depth,
            num_retain_entity=request.config.num_retain_entity,
            exploration_temp=request.config.exploration_temp,
            reasoning_temp=request.config.reasoning_temp,
            pruning_method=request.config.pruning_method,
            enable_sufficiency_check=request.config.enable_sufficiency_check,
            document_ids=request.document_ids,
        )

        # Process query with ToG reasoning
        reasoning_path = await tog_service.process_query(request.question, config)

        processing_time = time.time() - start_time

        # Record analytics
        try:
            tog_analytics.record_query_metrics(
                query_id=str(db_query.id) if 'db_query' in locals() else "unknown",
                question=request.question,
                config=config.__dict__ if hasattr(config, '__dict__') else config,
                reasoning_path=reasoning_path,
                processing_time_ms=int(processing_time * 1000),
                success=True
            )
        except Exception as e:
            logger.warning(f"Failed to record analytics: {e}")

        # Convert reasoning path to response schema
        response = ToGQueryResponse(
            answer=reasoning_path.final_answer or "No answer generated",
            reasoning_path=reasoning_path,  # Will be auto-converted by Pydantic
            query_type="tog",
            confidence_score=reasoning_path.confidence_score,
            processing_time=processing_time,
        )

        logger.info(f"ToG query completed in {processing_time:.2f}s")
        return response

    except Exception as e:
        logger.error(f"ToG query failed: {e}")
        processing_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail=f"ToG reasoning failed: {str(e)}"
        )


@router.post("/explain", response_model=ToGExplainResponse)
async def tog_explain(
    request: ToGExplainRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ToGExplainResponse:
    """
    Get detailed explanation of a ToG reasoning path.

    Args:
        request: Request with query ID to explain
        current_user: Current authenticated user
        db: Database session

    Returns:
        Detailed reasoning path explanation
    """
    # TODO: Implement in Phase 3 - for now return placeholder
    raise HTTPException(
        status_code=501,
        detail="ToG explanation endpoint not yet implemented"
    )


@router.post("/config", response_model=ToGConfigResponse)
async def tog_config(
    request: ToGConfigRequest,
    current_user: User = Depends(get_current_user),
) -> ToGConfigResponse:
    """
    Validate and set ToG configuration parameters.

    Args:
        request: ToG configuration to validate
        current_user: Current authenticated user

    Returns:
        Validated configuration response
    """
    try:
        # Basic validation
        validation_errors = []

        if request.config.search_width < 1 or request.config.search_width > 10:
            validation_errors.append("search_width must be between 1 and 10")

        if request.config.search_depth < 1 or request.config.search_depth > 5:
            validation_errors.append("search_depth must be between 1 and 5")

        if request.config.exploration_temp < 0.0 or request.config.exploration_temp > 1.0:
            validation_errors.append("exploration_temp must be between 0.0 and 1.0")

        if request.config.reasoning_temp < 0.0 or request.config.reasoning_temp > 1.0:
            validation_errors.append("reasoning_temp must be between 0.0 and 1.0")

        if request.config.pruning_method not in ["llm", "bm25", "sentence_bert"]:
            validation_errors.append("pruning_method must be one of: llm, bm25, sentence_bert")

        is_valid = len(validation_errors) == 0

        return ToGConfigResponse(
            config=request.config,
            is_valid=is_valid,
            validation_errors=validation_errors if not is_valid else None,
        )

    except Exception as e:
        logger.error(f"ToG config validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Configuration validation failed: {str(e)}"
        )


@router.get("/visualize/{query_id}")
async def get_reasoning_visualization(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get visualization data for a ToG reasoning path.

    Returns nodes, edges, and layout information for rendering
    the reasoning graph in the frontend.
    """
    # Fetch query from database
    db_query = db.query(Query).filter(
        Query.id == query_id,
        Query.user_id == current_user.id,
        Query.query_mode == "tog"
    ).first()

    if not db_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ToG query {query_id} not found"
        )

    try:
        # Reconstruct reasoning path from database
        # This is a simplified reconstruction - in practice you'd store the full object
        reasoning_path = {
            "steps": db_query.reasoning_path or [],
            "final_answer": db_query.response,
            "confidence_score": db_query.confidence_score or 0.0,
            "sufficiency_status": "unknown",
            "retrieved_triplets": db_query.retrieved_triplets or []
        }

        # Generate visualization data
        visualization_data = tog_visualization.generate_visualization_data(
            reasoning_path, db_query.question
        )

        return visualization_data

    except Exception as e:
        logger.error(f"Failed to generate visualization for query {query_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Visualization generation failed: {str(e)}"
        )


@router.get("/analytics/summary")
async def get_analytics_summary(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get analytics summary for ToG queries.

    Returns aggregate metrics and insights for query performance.
    """
    try:
        # Get aggregate metrics
        aggregates = tog_analytics.get_aggregate_metrics(time_range_hours=hours)

        # Get performance insights
        insights = tog_analytics.get_performance_insights()

        return {
            "aggregates": aggregates,
            "insights": insights,
            "time_range_hours": hours
        }

    except Exception as e:
        logger.error(f"Failed to generate analytics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics generation failed: {str(e)}"
        )
