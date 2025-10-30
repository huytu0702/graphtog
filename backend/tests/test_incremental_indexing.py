"""
Tests for incremental indexing functionality
Tests document version tracking, change detection, and incremental processing
"""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4

from app.models.document import Document
from app.services.document_processor import (
    compute_content_hash,
    detect_document_changes,
    process_document_incrementally,
)
from app.services.graph_service import graph_service
from app.services.community_detection import community_detection_service


class TestContentHashing:
    """Test content hashing for change detection"""

    def test_compute_content_hash(self):
        """Test SHA256 hash computation"""
        content1 = "Hello, World!"
        content2 = "Hello, World!"
        content3 = "Different content"

        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)
        hash3 = compute_content_hash(content3)

        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 character hex string

        # Different content should produce different hash
        assert hash1 != hash3

    def test_empty_content_hash(self):
        """Test hashing empty content"""
        empty_hash = compute_content_hash("")
        assert len(empty_hash) == 64
        assert isinstance(empty_hash, str)


class TestChangeDetection:
    """Test document change detection"""

    def test_detect_no_previous_hash(self, db):
        """Test change detection when document has no previous hash"""
        document = Document(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.md",
            file_path="/tmp/test.md",
            status="pending",
            version=1,
            content_hash=None,  # No previous hash
        )

        new_content = "# New Content\nSome text"
        result = detect_document_changes(document, new_content)

        assert result["has_changed"] is True
        assert result["old_hash"] is None
        assert result["new_hash"] is not None
        assert result["requires_reprocessing"] is True
        assert result["current_version"] == 1

    def test_detect_content_changed(self, db):
        """Test change detection when content has changed"""
        old_content = "# Old Content"
        old_hash = compute_content_hash(old_content)

        document = Document(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.md",
            file_path="/tmp/test.md",
            status="completed",
            version=1,
            content_hash=old_hash,
        )

        new_content = "# New Content\nThis is different"
        result = detect_document_changes(document, new_content)

        assert result["has_changed"] is True
        assert result["old_hash"] == old_hash
        assert result["new_hash"] != old_hash
        assert result["requires_reprocessing"] is True

    def test_detect_content_unchanged(self, db):
        """Test change detection when content is the same"""
        content = "# Same Content\nNo changes here"
        content_hash = compute_content_hash(content)

        document = Document(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.md",
            file_path="/tmp/test.md",
            status="completed",
            version=2,
            content_hash=content_hash,
        )

        result = detect_document_changes(document, content)

        assert result["has_changed"] is False
        assert result["old_hash"] == content_hash
        assert result["new_hash"] == content_hash
        assert result["requires_reprocessing"] is False
        assert result["current_version"] == 2


class TestGraphDataCleanup:
    """Test graph data cleanup for incremental updates"""

    def test_delete_document_graph_data_empty(self):
        """Test deleting graph data for non-existent document"""
        fake_doc_id = str(uuid4())
        result = graph_service.delete_document_graph_data(fake_doc_id)

        assert result["status"] == "success"
        assert result["textunits_deleted"] == 0
        assert result["entities_deleted"] == 0

    def test_get_affected_communities_empty(self):
        """Test getting affected communities for non-existent document"""
        fake_doc_id = str(uuid4())
        result = graph_service.get_affected_communities_for_document(fake_doc_id)

        assert result["num_communities"] == 0
        assert result["num_entities"] == 0
        assert result["community_ids"] == []
        assert result["affected_entities"] == []


class TestEntityUpdate:
    """Test entity update operations"""

    def test_update_nonexistent_entity(self):
        """Test updating an entity that doesn't exist"""
        fake_entity_id = "nonexistent_entity"
        result = graph_service.update_entity(
            entity_id=fake_entity_id,
            name="Updated Name",
            description="Updated description",
        )

        assert result is False

    def test_update_entity_confidence(self):
        """Test updating entity confidence score"""
        # This test requires an existing entity
        # In a real test, you would create an entity first
        pass


class TestIncrementalCommunityDetection:
    """Test incremental community detection"""

    def test_detect_communities_incrementally_empty_list(self):
        """Test incremental detection with empty entity list"""
        result = community_detection_service.detect_communities_incrementally(
            affected_entity_ids=[],
            seed=42,
        )

        assert result["status"] == "success"
        assert result["communities_recomputed"] == 0

    def test_detect_communities_incrementally_invalid_entities(self):
        """Test incremental detection with invalid entity IDs"""
        fake_entity_ids = ["fake_1", "fake_2", "fake_3"]
        result = community_detection_service.detect_communities_incrementally(
            affected_entity_ids=fake_entity_ids,
            seed=42,
        )

        # Should handle gracefully even with invalid IDs
        assert result["status"] in ["success", "error"]


class TestDocumentVersioning:
    """Test document version tracking"""

    def test_document_initial_version(self, db):
        """Test that new documents start at version 1"""
        document = Document(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.md",
            file_path="/tmp/test.md",
            status="pending",
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        assert document.version == 1
        assert document.content_hash is None
        assert document.last_processed_at is None

    def test_document_version_increment(self, db):
        """Test that document version increments on update"""
        document = Document(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.md",
            file_path="/tmp/test.md",
            status="completed",
            version=1,
            content_hash="initial_hash",
        )
        db.add(document)
        db.commit()

        # Simulate update
        document.version += 1
        document.content_hash = "new_hash"
        document.last_processed_at = datetime.utcnow()
        db.commit()
        db.refresh(document)

        assert document.version == 2
        assert document.content_hash == "new_hash"
        assert document.last_processed_at is not None


@pytest.mark.integration
class TestIncrementalProcessingIntegration:
    """Integration tests for incremental processing workflow"""

    @pytest.mark.asyncio
    async def test_incremental_processing_no_change(self, db, tmp_path):
        """Test that unchanged documents are not reprocessed"""
        # Create test file
        test_file = tmp_path / "test.md"
        content = "# Test Document\nSome content"
        test_file.write_text(content)

        # Create document with existing hash
        document = Document(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.md",
            file_path=str(test_file),
            status="completed",
            version=1,
            content_hash=compute_content_hash(content),
            last_processed_at=datetime.utcnow(),
        )
        db.add(document)
        db.commit()

        # Try incremental processing
        result = await process_document_incrementally(
            document_id=str(document.id),
            file_path=str(test_file),
            db=db,
        )

        # Should detect no changes and skip processing
        assert result["status"] == "success"
        assert result["content_changed"] is False
        assert "No changes detected" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_incremental_processing_with_change(self, db, tmp_path):
        """Test that changed documents are reprocessed"""
        # Create test file with initial content
        test_file = tmp_path / "test.md"
        initial_content = "# Test Document\nInitial content"
        test_file.write_text(initial_content)

        # Create document with old hash
        document = Document(
            id=uuid4(),
            user_id=uuid4(),
            filename="test.md",
            file_path=str(test_file),
            status="completed",
            version=1,
            content_hash=compute_content_hash(initial_content),
            last_processed_at=datetime.utcnow(),
        )
        db.add(document)
        db.commit()

        # Update file content
        new_content = "# Test Document\nUpdated content with changes"
        test_file.write_text(new_content)

        # Try incremental processing
        result = await process_document_incrementally(
            document_id=str(document.id),
            file_path=str(test_file),
            db=db,
        )

        # Should detect changes and reprocess
        assert result["content_changed"] is True
        assert result["incremental_update"] is True


class TestDocumentStatusUpdates:
    """Test document status tracking during updates"""

    def test_update_document_node_status(self):
        """Test updating document status in Neo4j"""
        # This test requires a document node in Neo4j
        fake_doc_id = str(uuid4())
        result = graph_service.update_document_node_status(
            document_id=fake_doc_id,
            status="processing",
        )

        # Should return False for non-existent document
        assert result is False


# Benchmark tests
@pytest.mark.benchmark
class TestIncrementalPerformance:
    """Performance benchmarks for incremental indexing"""

    @pytest.mark.asyncio
    async def test_change_detection_performance(self, benchmark, db, tmp_path):
        """Benchmark change detection performance"""
        test_file = tmp_path / "large.md"
        content = "# Large Document\n" + "Some content\n" * 1000
        test_file.write_text(content)

        document = Document(
            id=uuid4(),
            user_id=uuid4(),
            filename="large.md",
            file_path=str(test_file),
            status="completed",
            version=1,
            content_hash=compute_content_hash(content),
        )

        # Benchmark change detection
        def detect_change():
            return detect_document_changes(document, content)

        result = benchmark(detect_change)
        assert result["has_changed"] is False

    def test_hash_computation_performance(self, benchmark):
        """Benchmark hash computation for large documents"""
        large_content = "# Large Document\n" + "x" * 100000  # 100KB

        result = benchmark(compute_content_hash, large_content)
        assert len(result) == 64
