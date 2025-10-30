"""
Query API endpoints for Q&A functionality
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as QueryParam
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.models.query import Query
from app.services.query_service import query_service
from app.services.graph_service import graph_service
from app.services.auth import get_current_user
from app.models.user import User
from app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

router = APIRouter(tags=["queries"])


class QueryRequest(Dict):
    """Request model for query"""

    query: str
    hop_limit: int = 1


@router.post("")
async def create_query(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Process a query and get answer

    Args:
        request: QueryRequest with query text
        current_user: Current authenticated user
        db: Database session

    Returns:
        Query result with answer and citations
    """
    try:
        query_text = request.get("query", "").strip()
        hop_limit = request.get("hop_limit", 1)
        document_id = request.get("document_id")  # Optional

        # Get user_id from authenticated session
        user_id = current_user.id

        if not query_text:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        if len(query_text) > 1000:
            raise HTTPException(status_code=400, detail="Query too long (max 1000 characters)")

        # Process query
        logger.info(f"Processing query for user {user_id}: {query_text}")
        result = query_service.process_query(query_text, hop_limit, document_id)

        # Store query in database - only use fields that exist in Query model
        try:
            db_query = Query(
                user_id=user_id,
                document_id=document_id,
                query_text=query_text,
                response=result.get("answer", ""),  # Map answer to response
                reasoning_chain=str(result.get("context", "")),  # Map context to reasoning_chain
                query_mode=result.get("query_type", "unknown"),  # Map query_type to query_mode
                confidence_score=result.get("confidence_score", "0.0"),
            )
            db.add(db_query)
            db.commit()
            db.refresh(db_query)
            result["id"] = str(db_query.id)
        except Exception as e:
            logger.error(f"Error saving query to database: {e}")
            db.rollback()
            # Don't fail the entire query if DB save fails

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing error: {str(e)}")


@router.get("/{query_id}")
async def get_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Retrieve a previously processed query

    Args:
        query_id: ID of the query
        current_user: Current authenticated user
        db: Database session

    Returns:
        Query details
    """
    try:
        db_query = db.query(Query).filter(Query.id == query_id).first()

        if not db_query:
            raise HTTPException(status_code=404, detail="Query not found")

        # Check if query belongs to current user
        if db_query.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "id": str(db_query.id),
            "query_text": db_query.query_text,
            "query_mode": db_query.query_mode,  # Changed from query_type
            "response": db_query.response,  # Changed from answer
            "reasoning_chain": db_query.reasoning_chain,
            "confidence_score": db_query.confidence_score,
            "created_at": db_query.created_at.isoformat() if db_query.created_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving query: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving query")


@router.get("/results")
async def get_query_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """
    List recent query results for current user

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of queries
    """
    try:
        # Only get queries for current user
        queries = (
            db.query(Query)
            .filter(Query.user_id == current_user.id)
            .order_by(Query.created_at.desc())
            .limit(10)
            .all()
        )

        total = db.query(Query).filter(Query.user_id == current_user.id).count()

        return {
            "status": "success",
            "total": total,
            "queries": [
                {
                    "id": str(q.id),
                    "query_text": q.query_text,
                    "query_mode": q.query_mode,  # Changed from status
                    "response": q.response,  # Changed from answer
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in queries
            ],
        }

    except Exception as e:
        logger.error(f"Error listing queries: {e}")
        return {"status": "error", "message": str(e), "total": 0, "queries": []}


@router.get("")
async def list_queries(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """
    List queries for current user

    Args:
        skip: Number of queries to skip
        limit: Maximum number of queries to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of queries
    """
    try:
        # Only get queries for current user
        queries = (
            db.query(Query)
            .filter(Query.user_id == current_user.id)
            .order_by(Query.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        total = db.query(Query).filter(Query.user_id == current_user.id).count()

        return {
            "total": total,
            "queries": [
                {
                    "id": str(q.id),
                    "query_text": q.query_text,
                    "query_mode": q.query_mode,  # Changed from status
                    "response": q.response,  # Changed from answer
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in queries
            ],
        }

    except Exception as e:
        logger.error(f"Error listing queries: {e}")
        raise HTTPException(status_code=500, detail="Error listing queries")


@router.get("/graph/stats")
async def get_graph_statistics() -> Dict:
    """
    Get overall graph statistics

    Returns:
        Graph statistics
    """
    try:
        stats = graph_service.get_graph_statistics()

        return {
            "status": "success",
            "statistics": stats,
        }

    except Exception as e:
        logger.error(f"Error getting graph statistics: {e}")
        raise HTTPException(status_code=500, detail="Error getting graph statistics")


@router.post("/global")
async def process_global_query(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    use_mapreduce: Optional[bool] = QueryParam(None, description="Force Map-Reduce (auto if None)"),
) -> Dict:
    """
    Process a global/holistic query using community summaries (GraphRAG Global Search)

    Automatically uses Map-Reduce optimization when number of communities exceeds threshold.

    Best for:
    - Dataset-wide questions ("What are the main themes?")
    - High-level insights ("Summarize the key topics")
    - Holistic understanding ("What is this dataset about?")

    Args:
        request: Dict with "query" text and optional "batch_size"
        current_user: Current authenticated user
        db: Database session
        use_mapreduce: Force Map-Reduce on/off (auto-detect if None)

    Returns:
        Query result with community summaries and answer
    """
    try:
        query_text = request.get("query", "").strip()
        batch_size = request.get("batch_size", settings.MAPREDUCE_BATCH_SIZE)
        user_id = current_user.id

        if not query_text:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        if len(query_text) > 1000:
            raise HTTPException(status_code=400, detail="Query too long (max 1000 characters)")

        # Determine whether to use Map-Reduce
        should_use_mapreduce = use_mapreduce

        if should_use_mapreduce is None and settings.ENABLE_MAPREDUCE:
            # Auto-detect: check number of communities
            stats = graph_service.get_graph_statistics()
            num_communities = stats.get("communities", 0)
            should_use_mapreduce = num_communities >= settings.MAPREDUCE_THRESHOLD
            logger.info(
                f"Auto-detected {num_communities} communities, "
                f"using Map-Reduce: {should_use_mapreduce} "
                f"(threshold: {settings.MAPREDUCE_THRESHOLD})"
            )

        # Process global query with appropriate method
        logger.info(
            f"Processing global query for user {user_id} "
            f"(Map-Reduce: {should_use_mapreduce}): {query_text}"
        )

        if should_use_mapreduce:
            result = query_service.process_global_query_with_mapreduce(
                query_text, batch_size=batch_size
            )
        else:
            result = query_service.process_global_query(query_text)

        if result.get("status") == "error":
            error_message = result.get("error", "Unknown error")
            logger.error(f"Global query failed: {error_message}")
            raise HTTPException(status_code=500, detail=error_message)

        # Store query in database
        try:
            db_query = Query(
                user_id=user_id,
                document_id=None,  # Global queries span all documents
                query_text=query_text,
                response=result.get("answer", ""),
                reasoning_chain=result.get("context", ""),
                query_mode=result.get("query_type", "global"),
                confidence_score=result.get("confidence_score", "0.0"),
            )
            db.add(db_query)
            db.commit()
            db.refresh(db_query)
            result["id"] = str(db_query.id)
        except Exception as e:
            logger.error(f"Error saving global query to database: {e}")
            db.rollback()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Global query processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Global query error: {str(e)}")


@router.post("/batch-queries")
async def batch_process_queries(
    request: dict,
    db: Session = Depends(get_db),
) -> Dict:
    """
    Process multiple queries in batch

    Args:
        request: Dict with "queries" list
        db: Database session

    Returns:
        List of query results
    """
    try:
        queries = request.get("queries", [])

        if not queries:
            raise HTTPException(status_code=400, detail="No queries provided")

        if len(queries) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 queries per batch",
            )

        results = query_service.batch_process_queries(queries)

        return {
            "status": "success",
            "query_count": len(queries),
            "results": results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch query processing error: {e}")
        raise HTTPException(status_code=500, detail="Batch processing error")


@router.get("/claims")
async def get_all_claims(
    claim_type: Optional[str] = QueryParam(None, description="Filter by claim type"),
    status: Optional[str] = QueryParam(None, description="Filter by status (TRUE/FALSE/SUSPECTED)"),
    limit: int = QueryParam(100, ge=1, le=500, description="Maximum number of claims"),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    Get all claims in the graph with optional filters

    Args:
        claim_type: Filter by claim type (optional)
        status: Filter by status (optional)
        limit: Maximum number of claims to return
        current_user: Current authenticated user

    Returns:
        List of claims with metadata
    """
    try:
        logger.info(
            f"User {current_user.id} requesting claims "
            f"(type={claim_type}, status={status}, limit={limit})"
        )

        result = query_service.get_all_claims(
            claim_type=claim_type,
            status=status,
            limit=limit,
        )

        if result.get("status") == "error":
            error_message = result.get("error", "Unknown error")
            logger.error(f"Get claims failed: {error_message}")
            raise HTTPException(status_code=500, detail=error_message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get claims error: {e}")
        raise HTTPException(status_code=500, detail=f"Get claims error: {str(e)}")


@router.get("/claims/entity/{entity_name}")
async def get_claims_for_entity(
    entity_name: str,
    limit: int = QueryParam(20, ge=1, le=100, description="Maximum number of claims"),
    current_user: User = Depends(get_current_user),
) -> Dict:
    """
    Get all claims related to a specific entity

    Args:
        entity_name: Name of the entity
        limit: Maximum number of claims to return
        current_user: Current authenticated user

    Returns:
        List of claims for the entity
    """
    try:
        logger.info(
            f"User {current_user.id} requesting claims for entity: {entity_name}"
        )

        result = query_service.get_claims_for_entity(
            entity_name=entity_name,
            limit=limit,
        )

        if result.get("status") == "error":
            error_message = result.get("error", "Unknown error")
            logger.error(f"Get claims for entity failed: {error_message}")
            raise HTTPException(status_code=500, detail=error_message)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get claims for entity error: {e}")
        raise HTTPException(status_code=500, detail=f"Get claims error: {str(e)}")


@router.post("/claims/query")
async def query_claims(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Query claims with natural language and optional filters

    Best for:
    - Finding claims about specific entities
    - Filtering claims by type or status
    - Asking questions about extracted claims

    Args:
        request: Dict with "query" text and optional filters
        current_user: Current authenticated user
        db: Database session

    Returns:
        Query result with filtered claims and answer
    """
    try:
        query_text = request.get("query", "").strip()
        entity_name = request.get("entity_name")
        claim_type = request.get("claim_type")
        status = request.get("status")
        limit = request.get("limit", 20)
        user_id = current_user.id

        if not query_text:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        if len(query_text) > 1000:
            raise HTTPException(status_code=400, detail="Query too long (max 1000 characters)")

        logger.info(
            f"Processing claims query for user {user_id}: {query_text} "
            f"(entity={entity_name}, type={claim_type}, status={status})"
        )

        result = query_service.query_claims(
            query=query_text,
            entity_name=entity_name,
            claim_type=claim_type,
            status=status,
            limit=limit,
        )

        if result.get("status") == "error":
            error_message = result.get("error", "Unknown error")
            logger.error(f"Claims query failed: {error_message}")
            raise HTTPException(status_code=500, detail=error_message)

        # Store query in database (optional)
        try:
            db_query = Query(
                user_id=user_id,
                document_id=None,
                query_text=query_text,
                response=result.get("answer", ""),
                reasoning_chain=str(result.get("filters", "")),
                query_mode="claims",
                confidence_score="0.9",
            )
            db.add(db_query)
            db.commit()
            db.refresh(db_query)
            result["id"] = str(db_query.id)
        except Exception as e:
            logger.error(f"Error saving claims query to database: {e}")
            db.rollback()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Claims query processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Claims query error: {str(e)}")
