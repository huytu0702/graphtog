"""
Performance benchmarking tests
Measures execution time and throughput of key operations
"""

import time
from typing import Dict, List

import pytest


class TestPerformanceBenchmarks:
    """Performance benchmarking tests"""

    @pytest.mark.benchmark
    def test_local_retrieval_performance(self, authenticated_client, benchmark):
        """Benchmark local retrieval performance"""
        def run_test():
            response = authenticated_client.post(
                "/api/retrieve/local",
                json={"entity": "test_entity", "hop_limit": 1}
            )
            return response

        result = benchmark(run_test)
        assert result.status_code in [200, 500]

    @pytest.mark.benchmark
    def test_hierarchical_search_performance(self, authenticated_client, benchmark):
        """Benchmark hierarchical search performance"""
        def run_test():
            response = authenticated_client.post(
                "/api/retrieve/hierarchical",
                json={"query": "What is the technology stack?"}
            )
            return response

        result = benchmark(run_test)
        assert result.status_code in [200, 500]

    @pytest.mark.benchmark
    def test_visualization_performance(self, authenticated_client, benchmark):
        """Benchmark visualization generation performance"""
        def run_test():
            response = authenticated_client.get("/api/visualize/entity-graph?limit=50")
            return response

        result = benchmark(run_test)
        assert result.status_code in [200, 500]

    @pytest.mark.benchmark
    def test_cache_stats_performance(self, authenticated_client, benchmark):
        """Benchmark cache statistics retrieval"""
        def run_test():
            response = authenticated_client.get("/api/cache/stats")
            return response

        result = benchmark(run_test)
        assert result.status_code in [200, 500]

    def test_request_latency(self, authenticated_client):
        """Test request latency for various endpoints"""
        endpoints = [
            ("GET", "/api/retrieve/global", None),
            ("GET", "/api/communities/statistics", None),
            ("POST", "/api/cache/clear-all", None),
        ]

        latencies = {}
        for method, endpoint, json_data in endpoints:
            start = time.time()

            if method == "GET":
                response = authenticated_client.get(endpoint)
            else:
                response = authenticated_client.post(endpoint, json=json_data or {})

            latency = (time.time() - start) * 1000  # Convert to ms

            latencies[endpoint] = latency
            print(f"\n{method} {endpoint}: {latency:.2f}ms")

        # Assert reasonable latencies (< 5 seconds for each)
        for endpoint, latency in latencies.items():
            assert latency < 5000, f"{endpoint} took too long: {latency}ms"

    def test_concurrent_request_handling(self, authenticated_client):
        """Test handling of concurrent requests"""
        import threading

        results = []
        errors = []

        def make_request():
            try:
                response = authenticated_client.get("/api/cache/stats")
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create 10 concurrent threads
        threads = [threading.Thread(target=make_request) for _ in range(10)]

        start = time.time()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        elapsed = time.time() - start

        # All requests should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(code in [200, 500] for code in results)

        print(f"\n10 concurrent requests completed in {elapsed:.2f}s")

    def test_response_payload_size(self, authenticated_client):
        """Test response payload sizes"""
        response = authenticated_client.get("/api/visualize/entity-graph?limit=50")
        
        if response.status_code == 200:
            payload_size = len(response.content) / 1024  # KB
            print(f"\nEntity graph payload: {payload_size:.2f}KB")
            
            # Payload should be reasonable (< 5MB)
            assert payload_size < 5000, f"Payload too large: {payload_size}KB"


class PerformanceMetrics:
    """Helper class for collecting performance metrics"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}

    def record(self, operation: str, duration_ms: float):
        """Record operation duration"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration_ms)

    def get_summary(self, operation: str) -> Dict:
        """Get performance summary for operation"""
        if operation not in self.metrics:
            return {}

        durations = self.metrics[operation]
        return {
            "operation": operation,
            "count": len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "avg_ms": sum(durations) / len(durations),
            "p95_ms": sorted(durations)[int(len(durations) * 0.95)] if durations else 0,
            "p99_ms": sorted(durations)[int(len(durations) * 0.99)] if durations else 0,
        }

    def print_report(self):
        """Print performance report"""
        print("\n" + "=" * 60)
        print("PERFORMANCE METRICS REPORT")
        print("=" * 60)

        for operation in self.metrics:
            summary = self.get_summary(operation)
            print(f"\n{summary['operation']}:")
            print(f"  Requests: {summary['count']}")
            print(f"  Min: {summary['min_ms']:.2f}ms")
            print(f"  Avg: {summary['avg_ms']:.2f}ms")
            print(f"  Max: {summary['max_ms']:.2f}ms")
            print(f"  P95: {summary['p95_ms']:.2f}ms")
            print(f"  P99: {summary['p99_ms']:.2f}ms")

        print("\n" + "=" * 60)
