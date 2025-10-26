"""
Query API endpoints for Q&A functionality
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.models.query import QueryModel
from app.services.query_service import query_service
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["queries"])


class QueryRequest(Dict):
    """Request model for query"""

    query: str
    hop_limit: int = 1


@router.post("/queries")
async def create_query(
    request: dict,
    db: Session = Depends(get_db),
) -> Dict:
    """
    Process a query and get answer

    Args:
        request: QueryRequest with query text
        db: Database session

    Returns:
        Query result with answer and citations
    """
    try:
        query_text = request.get("query", "").strip()
        hop_limit = request.get("hop_limit", 1)

        if not query_text:
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        if len(query_text) > 1000:
            raise HTTPException(status_code=400, detail="Query too long (max 1000 characters)")

        # Process query
        logger.info(f"Processing query: {query_text}")
        result = query_service.process_query(query_text, hop_limit)

        # Store query in database
        try:
            db_query = QueryModel(
                query_text=query_text,
                query_type=result.get("query_type", "unknown"),
                status=result["status"],
                entities_found=result.get("entities_found", []),
                answer=result.get("answer", ""),
                citations=result.get("citations", []),
            )
            db.add(db_query)
            db.commit()
            db.refresh(db_query)
            result["id"] = db_query.id
        except Exception as e:
            logger.error(f"Error saving query to database: {e}")
            db.rollback()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing error: {str(e)}")


@router.get("/queries/{query_id}")
async def get_query(
    query_id: int,
    db: Session = Depends(get_db),
) -> Dict:
    """
    Retrieve a previously processed query

    Args:
        query_id: ID of the query
        db: Database session

    Returns:
        Query details
    """
    try:
        db_query = db.query(QueryModel).filter(QueryModel.id == query_id).first()

        if not db_query:
            raise HTTPException(status_code=404, detail="Query not found")

        return {
            "id": db_query.id,
            "query_text": db_query.query_text,
            "query_type": db_query.query_type,
            "status": db_query.status,
            "entities_found": db_query.entities_found,
            "answer": db_query.answer,
            "citations": db_query.citations,
            "created_at": db_query.created_at.isoformat() if db_query.created_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving query: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving query")


@router.get("/queries")
async def list_queries(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Dict:
    """
    List recent queries

    Args:
        skip: Number of queries to skip
        limit: Maximum number of queries to return
        db: Database session

    Returns:
        List of queries
    """
    try:
        queries = (
            db.query(QueryModel)
            .order_by(QueryModel.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        total = db.query(QueryModel).count()

        return {
            "total": total,
            "queries": [
                {
                    "id": q.id,
                    "query_text": q.query_text,
                    "status": q.status,
                    "entities_found": q.entities_found,
                    "answer": q.answer,
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
