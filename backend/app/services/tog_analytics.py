"""
ToG Query Analytics Service.

Tracks, analyzes, and reports on ToG query performance, usage patterns,
and reasoning effectiveness metrics.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

logger = logging.getLogger(__name__)


class ToGAnalyticsService:
    """Service for analyzing ToG query performance and patterns."""

    def __init__(self, db_session=None):
        self.db_session = db_session
        self.metrics_cache = {}
        self.cache_ttl = 300  # 5 minutes

    def record_query_metrics(
        self,
        query_id: str,
        question: str,
        config: Dict[str, Any],
        reasoning_path: Any,  # ToGReasoningPath
        processing_time_ms: int,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Record detailed metrics for a completed ToG query.

        Args:
            query_id: Unique query identifier
            question: Original question
            config: ToG configuration used
            reasoning_path: Complete reasoning path
            processing_time_ms: Total processing time
            success: Whether the query completed successfully
            error_message: Error message if failed
        """
        try:
            metrics = self._extract_query_metrics(
                query_id, question, config, reasoning_path,
                processing_time_ms, success, error_message
            )

            # Store in database if available
            if self.db_session:
                self._store_metrics_in_db(metrics)

            # Update in-memory cache
            self._update_cache(metrics)

            logger.info(f"Recorded analytics for ToG query {query_id}")

        except Exception as e:
            logger.error(f"Failed to record query metrics: {e}")

    def _extract_query_metrics(
        self, query_id: str, question: str, config: Dict[str, Any],
        reasoning_path: Any, processing_time_ms: int, success: bool,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract comprehensive metrics from a ToG query execution."""

        metrics = {
            "query_id": query_id,
            "timestamp": datetime.utcnow().isoformat(),
            "question": question,
            "question_length": len(question),
            "success": success,
            "error_message": error_message,

            # Configuration metrics
            "config": {
                "search_width": config.get("search_width", 3),
                "search_depth": config.get("search_depth", 3),
                "num_retain_entity": config.get("num_retain_entity", 5),
                "exploration_temp": config.get("exploration_temp", 0.4),
                "reasoning_temp": config.get("reasoning_temp", 0.0),
                "pruning_method": config.get("pruning_method", "llm"),
                "enable_sufficiency_check": config.get("enable_sufficiency_check", True),
                "document_ids_count": len(config.get("document_ids") or [])
            },

            # Performance metrics
            "performance": {
                "total_time_ms": processing_time_ms,
                "avg_time_per_step": 0,
                "time_distribution": {}
            },

            # Reasoning metrics
            "reasoning": {
                "total_steps": len(reasoning_path.steps),
                "max_depth_reached": max((s.depth for s in reasoning_path.steps), default=0),
                "entities_explored": sum(len(s.entities_explored) for s in reasoning_path.steps),
                "relations_selected": sum(len(s.relations_selected) for s in reasoning_path.steps),
                "triplets_retrieved": len(getattr(reasoning_path, 'retrieved_triplets', [])),
                "sufficiency_status": reasoning_path.sufficiency_status,
                "final_confidence": reasoning_path.confidence_score
            },

            # Quality metrics
            "quality": {
                "answer_length": len(reasoning_path.final_answer or ""),
                "avg_entity_confidence": 0,
                "avg_relation_confidence": 0,
                "sufficiency_scores": []
            },

            # Efficiency metrics
            "efficiency": {
                "entities_per_step": 0,
                "relations_per_step": 0,
                "exploration_efficiency": 0,  # triplets / entities_explored
                "depth_utilization": 0  # max_depth / configured_depth
            }
        }

        # Calculate derived metrics
        self._calculate_derived_metrics(metrics, reasoning_path, config)

        return metrics

    def _calculate_derived_metrics(
        self, metrics: Dict[str, Any], reasoning_path: Any, config: Dict[str, Any]
    ) -> None:
        """Calculate derived metrics from raw data."""

        reasoning = metrics["reasoning"]
        performance = metrics["performance"]
        quality = metrics["quality"]
        efficiency = metrics["efficiency"]

        # Performance calculations
        if reasoning["total_steps"] > 0:
            performance["avg_time_per_step"] = performance["total_time_ms"] / reasoning["total_steps"]

        # Quality calculations
        if reasoning_path.steps:
            sufficiency_scores = [
                s.sufficiency_score for s in reasoning_path.steps
                if s.sufficiency_score is not None
            ]
            if sufficiency_scores:
                quality["sufficiency_scores"] = sufficiency_scores

        # Entity and relation confidences
        entity_confidences = []
        relation_confidences = []

        for step in reasoning_path.steps:
            for entity in step.entities_explored:
                entity_confidences.append(entity.confidence)

            for relation in step.relations_selected:
                relation_confidences.append(relation.confidence)

        if entity_confidences:
            quality["avg_entity_confidence"] = statistics.mean(entity_confidences)

        if relation_confidences:
            quality["avg_relation_confidence"] = statistics.mean(relation_confidences)

        # Efficiency calculations
        if reasoning["total_steps"] > 0:
            efficiency["entities_per_step"] = reasoning["entities_explored"] / reasoning["total_steps"]
            efficiency["relations_per_step"] = reasoning["relations_selected"] / reasoning["total_steps"]

        if reasoning["entities_explored"] > 0:
            efficiency["exploration_efficiency"] = reasoning["triplets_retrieved"] / reasoning["entities_explored"]

        configured_depth = config.get("search_depth", 3)
        if configured_depth > 0:
            efficiency["depth_utilization"] = reasoning["max_depth_reached"] / configured_depth

    def _store_metrics_in_db(self, metrics: Dict[str, Any]) -> None:
        """Store metrics in database for long-term analysis."""
        try:
            # This would create a ToGAnalytics model and store the metrics
            # For now, we'll just log that we'd store it
            logger.debug(f"Would store metrics for query {metrics['query_id']} in database")

            # TODO: Implement actual database storage
            # tog_analytics = ToGAnalytics(**metrics)
            # self.db_session.add(tog_analytics)
            # self.db_session.commit()

        except Exception as e:
            logger.error(f"Failed to store metrics in database: {e}")

    def _update_cache(self, metrics: Dict[str, Any]) -> None:
        """Update in-memory cache with latest metrics."""
        query_id = metrics["query_id"]
        self.metrics_cache[query_id] = {
            "data": metrics,
            "timestamp": time.time()
        }

        # Clean old cache entries
        self._clean_cache()

    def _clean_cache(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, data in self.metrics_cache.items()
            if current_time - data["timestamp"] > self.cache_ttl
        ]

        for key in expired_keys:
            del self.metrics_cache[key]

    def get_query_metrics(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metrics for a specific query."""
        return self.metrics_cache.get(query_id, {}).get("data")

    def get_aggregate_metrics(
        self, time_range_hours: int = 24, limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Get aggregate metrics across multiple queries.

        Args:
            time_range_hours: Hours of history to analyze
            limit: Maximum queries to analyze

        Returns:
            Dictionary with aggregate statistics
        """
        # Get recent metrics from cache
        recent_metrics = []
        cutoff_time = time.time() - (time_range_hours * 3600)

        for data in self.metrics_cache.values():
            if data["timestamp"] > cutoff_time:
                recent_metrics.append(data["data"])
                if len(recent_metrics) >= limit:
                    break

        if not recent_metrics:
            return self._empty_aggregate_metrics()

        return self._calculate_aggregate_metrics(recent_metrics)

    def _calculate_aggregate_metrics(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregate statistics from a list of metrics."""

        total_queries = len(metrics_list)
        successful_queries = sum(1 for m in metrics_list if m["success"])

        # Performance aggregates
        processing_times = [m["performance"]["total_time_ms"] for m in metrics_list]
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0

        # Reasoning aggregates
        total_steps = [m["reasoning"]["total_steps"] for m in metrics_list]
        avg_steps = statistics.mean(total_steps) if total_steps else 0

        entities_explored = [m["reasoning"]["entities_explored"] for m in metrics_list]
        avg_entities = statistics.mean(entities_explored) if entities_explored else 0

        # Configuration usage
        pruning_methods = Counter(m["config"]["pruning_method"] for m in metrics_list)
        search_widths = Counter(m["config"]["search_width"] for m in metrics_list)

        # Quality metrics
        confidences = [m["reasoning"]["final_confidence"] for m in metrics_list if m["reasoning"]["final_confidence"] > 0]
        avg_confidence = statistics.mean(confidences) if confidences else 0

        return {
            "summary": {
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "success_rate": successful_queries / total_queries if total_queries > 0 else 0,
                "time_range_hours": 24
            },

            "performance": {
                "avg_processing_time_ms": avg_processing_time,
                "min_processing_time_ms": min(processing_times) if processing_times else 0,
                "max_processing_time_ms": max(processing_times) if processing_times else 0,
                "processing_time_p95": statistics.quantiles(processing_times, n=20)[18] if len(processing_times) >= 20 else avg_processing_time
            },

            "reasoning": {
                "avg_steps_per_query": avg_steps,
                "avg_entities_explored": avg_entities,
                "most_common_sufficiency_status": Counter(
                    m["reasoning"]["sufficiency_status"] for m in metrics_list
                ).most_common(1)[0][0] if metrics_list else "unknown"
            },

            "quality": {
                "avg_final_confidence": avg_confidence,
                "confidence_distribution": self._calculate_distribution(confidences)
            },

            "configuration": {
                "pruning_method_usage": dict(pruning_methods),
                "search_width_usage": dict(search_widths)
            },

            "trends": self._calculate_trends(metrics_list)
        }

    def _empty_aggregate_metrics(self) -> Dict[str, Any]:
        """Return empty aggregate metrics structure."""
        return {
            "summary": {
                "total_queries": 0,
                "successful_queries": 0,
                "success_rate": 0,
                "time_range_hours": 24
            },
            "performance": {},
            "reasoning": {},
            "quality": {},
            "configuration": {},
            "trends": {}
        }

    def _calculate_distribution(self, values: List[float], bins: int = 5) -> Dict[str, int]:
        """Calculate distribution of values into bins."""
        if not values:
            return {}

        min_val, max_val = min(values), max(values)
        if min_val == max_val:
            return {f"{min_val:.2f}": len(values)}

        bin_size = (max_val - min_val) / bins
        distribution = {}

        for i in range(bins):
            bin_start = min_val + (i * bin_size)
            bin_end = min_val + ((i + 1) * bin_size)
            count = sum(1 for v in values if bin_start <= v < bin_end)
            if count > 0:
                distribution[f"{bin_start:.2f}-{bin_end:.2f}"] = count

        return distribution

    def _calculate_trends(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trends over time."""
        # Sort by timestamp
        sorted_metrics = sorted(metrics_list, key=lambda m: m["timestamp"])

        if len(sorted_metrics) < 2:
            return {"insufficient_data": True}

        # Simple trend calculation (comparing first half vs second half)
        midpoint = len(sorted_metrics) // 2
        first_half = sorted_metrics[:midpoint]
        second_half = sorted_metrics[midpoint:]

        def avg_metric(metrics, key_path):
            values = []
            for m in metrics:
                value = m
                for key in key_path.split('.'):
                    value = value.get(key, 0)
                values.append(value)
            return statistics.mean(values) if values else 0

        return {
            "processing_time_trend": self._calculate_trend_direction(
                avg_metric(first_half, "performance.total_time_ms"),
                avg_metric(second_half, "performance.total_time_ms")
            ),
            "confidence_trend": self._calculate_trend_direction(
                avg_metric(first_half, "reasoning.final_confidence"),
                avg_metric(second_half, "reasoning.final_confidence")
            ),
            "steps_trend": self._calculate_trend_direction(
                avg_metric(first_half, "reasoning.total_steps"),
                avg_metric(second_half, "reasoning.total_steps")
            )
        }

    def _calculate_trend_direction(self, first_avg: float, second_avg: float) -> str:
        """Calculate trend direction from two averages."""
        if abs(second_avg - first_avg) / max(abs(first_avg), 0.001) < 0.05:
            return "stable"
        elif second_avg > first_avg:
            return "increasing"
        else:
            return "decreasing"

    def get_performance_insights(self) -> Dict[str, Any]:
        """Generate performance insights and recommendations."""
        aggregates = self.get_aggregate_metrics()

        insights = {
            "bottlenecks": [],
            "recommendations": [],
            "anomalies": []
        }

        # Analyze performance bottlenecks
        if aggregates["performance"].get("avg_processing_time_ms", 0) > 5000:
            insights["bottlenecks"].append("High average processing time (>5s)")

        if aggregates["reasoning"].get("avg_steps_per_query", 0) > 3:
            insights["bottlenecks"].append("High average reasoning steps")

        # Generate recommendations
        if aggregates["summary"].get("success_rate", 1) < 0.9:
            insights["recommendations"].append("Investigate query failures - success rate below 90%")

        pruning_usage = aggregates["configuration"].get("pruning_method_usage", {})
        if pruning_usage.get("llm", 0) > pruning_usage.get("bm25", 0) * 2:
            insights["recommendations"].append("Consider using BM25 pruning for faster queries")

        return insights
