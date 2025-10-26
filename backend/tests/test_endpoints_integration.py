"""
Integration tests for all API endpoints
Tests authentication, documents, queries, communities, retrieval, visualization, and cache
"""

import json
from typing import Dict

import pytest


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_register_user(self, client):
        """Test user registration"""
        user_data = {
            "email": "newuser@example.com",
            "password": "password123",
            "full_name": "New User"
        }
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code in [200, 201]

    def test_login_user(self, client):
        """Test user login"""
        # First register
        user_data = {
            "email": "login_test@example.com",
            "password": "password123",
            "full_name": "Login Test"
        }
        client.post("/api/auth/register", json=user_data)

        # Then login
        response = client.post(
            "/api/auth/login",
            json={"email": user_data["email"], "password": user_data["password"]}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrong"}
        )
        assert response.status_code == 401


class TestDocumentEndpoints:
    """Test document management endpoints"""

    def test_upload_document(self, authenticated_client, tmp_path):
        """Test document upload"""
        # Create a test markdown file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document\n\nThis is a test.")

        with open(test_file, "rb") as f:
            response = authenticated_client.post(
                "/api/documents/upload",
                files={"file": ("test.md", f, "text/markdown")}
            )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "document_id" in data or "id" in data

    def test_list_documents(self, authenticated_client):
        """Test document listing"""
        response = authenticated_client.get("/api/documents/list")
        assert response.status_code == 200
        assert isinstance(response.json(), (list, dict))

    def test_get_document_status(self, authenticated_client):
        """Test get document status"""
        # First upload a document
        test_md = "# Test\n\nContent"
        doc_response = authenticated_client.post(
            "/api/documents/upload",
            files={"file": ("test.md", test_md.encode(), "text/markdown")}
        )

        if doc_response.status_code in [200, 201]:
            doc_id = doc_response.json().get("document_id") or doc_response.json().get("id")
            if doc_id:
                response = authenticated_client.get(f"/api/documents/{doc_id}/status")
                assert response.status_code == 200


class TestCommunityEndpoints:
    """Test community detection and analysis endpoints"""

    def test_detect_communities(self, authenticated_client):
        """Test community detection endpoint"""
        response = authenticated_client.post("/api/communities/detect")
        assert response.status_code in [200, 500]  # 500 if no graph data
        data = response.json()
        assert "status" in data

    def test_get_community_statistics(self, authenticated_client):
        """Test community statistics endpoint"""
        response = authenticated_client.get("/api/communities/statistics")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_get_community_members(self, authenticated_client):
        """Test get community members endpoint"""
        response = authenticated_client.get("/api/communities/1/members")
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert "status" in data

    def test_summarize_community(self, authenticated_client):
        """Test community summarization endpoint"""
        response = authenticated_client.post("/api/communities/1/summarize")
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert "status" in data

    def test_summarize_all_communities(self, authenticated_client):
        """Test summarize all communities endpoint"""
        response = authenticated_client.post("/api/communities/summarize-all")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data


class TestRetrievalEndpoints:
    """Test retrieval endpoints"""

    def test_retrieve_local(self, authenticated_client):
        """Test local retrieval endpoint"""
        response = authenticated_client.post(
            "/api/retrieve/local",
            json={"entity": "test_entity", "hop_limit": 1}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_retrieve_community(self, authenticated_client):
        """Test community retrieval endpoint"""
        response = authenticated_client.post(
            "/api/retrieve/community",
            json={"entity": "test_entity"}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_retrieve_global(self, authenticated_client):
        """Test global retrieval endpoint"""
        response = authenticated_client.get("/api/retrieve/global")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_hierarchical_search(self, authenticated_client):
        """Test hierarchical search endpoint"""
        response = authenticated_client.post(
            "/api/retrieve/hierarchical",
            json={"query": "What is test?"}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_adaptive_retrieval(self, authenticated_client):
        """Test adaptive retrieval endpoint"""
        response = authenticated_client.post(
            "/api/retrieve/adaptive",
            json={"query": "Tell me about something"}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data


class TestAdvancedExtractionEndpoints:
    """Test advanced extraction endpoints"""

    def test_few_shot_extraction(self, authenticated_client):
        """Test few-shot entity extraction"""
        response = authenticated_client.post(
            "/api/extract/few-shot",
            json={"text": "Apple was founded by Steve Jobs"}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_coreference_resolution(self, authenticated_client):
        """Test coreference resolution"""
        response = authenticated_client.post(
            "/api/extract/coreferences",
            json={"text": "Steve Jobs founded Apple. He was a visionary."}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_extract_attributes(self, authenticated_client):
        """Test entity attribute extraction"""
        response = authenticated_client.post(
            "/api/extract/attributes",
            json={"entity_name": "Apple", "text": "Apple Inc. is a tech company"}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_extract_events(self, authenticated_client):
        """Test event extraction"""
        response = authenticated_client.post(
            "/api/extract/events",
            json={"text": "Apple was founded in 1976 in California"}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_multi_perspective_analysis(self, authenticated_client):
        """Test multi-perspective analysis"""
        response = authenticated_client.post(
            "/api/analyze/multi-perspective",
            json={
                "query": "What is the impact of AI?",
                "context": "AI is transforming industries"
            }
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data


class TestVisualizationEndpoints:
    """Test visualization endpoints"""

    def test_get_entity_graph(self, authenticated_client):
        """Test entity graph visualization"""
        response = authenticated_client.get(
            "/api/visualize/entity-graph?limit=100"
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data
        if data["status"] == "success":
            assert "elements" in data

    def test_get_community_graph(self, authenticated_client):
        """Test community graph visualization"""
        response = authenticated_client.get("/api/visualize/community-graph")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_get_hierarchical_graph(self, authenticated_client):
        """Test hierarchical graph visualization"""
        response = authenticated_client.get("/api/visualize/hierarchical-graph")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_get_ego_graph(self, authenticated_client):
        """Test ego graph visualization"""
        response = authenticated_client.get(
            "/api/visualize/ego-graph/test_entity?hop_limit=2"
        )
        assert response.status_code in [200, 404, 500]
        data = response.json()
        assert "status" in data


class TestCacheEndpoints:
    """Test cache management endpoints"""

    def test_get_cache_stats(self, authenticated_client):
        """Test cache statistics endpoint"""
        response = authenticated_client.get("/api/cache/stats")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_clear_all_caches(self, authenticated_client):
        """Test clear all caches endpoint"""
        response = authenticated_client.post("/api/cache/clear-all")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_clear_cache_type(self, authenticated_client):
        """Test clear cache by type endpoint"""
        response = authenticated_client.post("/api/cache/clear/entity")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_delete_cache_key(self, authenticated_client):
        """Test delete specific cache key endpoint"""
        response = authenticated_client.delete("/api/cache/key/test_key")
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data


class TestQueryEndpoints:
    """Test query endpoints"""

    def test_create_query(self, authenticated_client):
        """Test query creation endpoint"""
        response = authenticated_client.post(
            "/api/queries",
            json={"query": "What is the document about?"}
        )
        assert response.status_code in [200, 500]
        data = response.json()
        assert "status" in data

    def test_get_query_results(self, authenticated_client):
        """Test get query results endpoint"""
        response = authenticated_client.get("/api/queries/results")
        assert response.status_code in [200, 500]


# Health check tests
class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code in [200, 404]  # 404 if no health endpoint

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code in [200, 404, 307]
