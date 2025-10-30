"""
Tests for entity resolution and disambiguation functionality
"""

import pytest
from app.services.entity_resolution import entity_resolution_service
from app.services.graph_service import graph_service


class TestEntitySimilarity:
    """Tests for entity similarity calculation"""

    def test_exact_match_similarity(self):
        """Test that exact matches return 1.0"""
        similarity = entity_resolution_service.calculate_similarity("Microsoft", "Microsoft")
        assert similarity == 1.0

    def test_case_insensitive_similarity(self):
        """Test that comparison is case-insensitive"""
        similarity = entity_resolution_service.calculate_similarity("Microsoft", "microsoft")
        assert similarity == 1.0

    def test_whitespace_normalized(self):
        """Test that whitespace is normalized"""
        similarity = entity_resolution_service.calculate_similarity("  Microsoft  ", "Microsoft")
        assert similarity == 1.0

    def test_similar_strings_high_score(self):
        """Test that similar strings get high similarity scores"""
        similarity = entity_resolution_service.calculate_similarity("Microsoft", "Microsft")
        assert similarity > 0.85

    def test_very_different_strings_low_score(self):
        """Test that very different strings get low scores"""
        similarity = entity_resolution_service.calculate_similarity("Microsoft", "Apple")
        assert similarity < 0.5

    def test_abbreviation_similarity(self):
        """Test similarity between abbreviations"""
        # "MS" vs "Microsoft" should have some similarity but not high
        similarity = entity_resolution_service.calculate_similarity("MS", "Microsoft")
        assert 0.0 < similarity < 0.5


@pytest.mark.integration
class TestFindSimilarEntities:
    """Integration tests for finding similar entities in graph"""

    @pytest.fixture(autouse=True)
    def setup_test_entities(self):
        """Create test entities in graph before each test"""
        # Initialize schema
        graph_service.init_schema()

        # Create test entities
        self.entity1_id = graph_service.create_or_merge_entity(
            name="Microsoft Corporation",
            entity_type="ORGANIZATION",
            description="Technology company",
            confidence=0.9,
        )

        self.entity2_id = graph_service.create_or_merge_entity(
            name="Microsoft Corp",
            entity_type="ORGANIZATION",
            description="Tech company",
            confidence=0.85,
        )

        self.entity3_id = graph_service.create_or_merge_entity(
            name="Apple Inc",
            entity_type="ORGANIZATION",
            description="Technology company",
            confidence=0.9,
        )

        yield

        # Cleanup: Delete test entities
        session = graph_service.get_session()
        session.run("MATCH (e:Entity) WHERE e.id IN [$id1, $id2, $id3] DETACH DELETE e",
                    id1=self.entity1_id, id2=self.entity2_id, id3=self.entity3_id)

    def test_find_similar_entities_success(self):
        """Test finding similar entities"""
        similar = entity_resolution_service.find_similar_entities(
            entity_name="Microsoft Corporation",
            entity_type="ORGANIZATION",
            threshold=0.7,
        )

        # Should find "Microsoft Corp" but not "Apple Inc"
        assert len(similar) >= 1
        names = [e["name"] for e in similar]
        assert "Microsoft Corp" in names
        assert "Apple Inc" not in names

    def test_find_similar_entities_with_high_threshold(self):
        """Test that high threshold filters results"""
        similar = entity_resolution_service.find_similar_entities(
            entity_name="Microsoft Corporation",
            entity_type="ORGANIZATION",
            threshold=0.99,  # Very high threshold
        )

        # Should find very few or no matches
        assert len(similar) <= 1

    def test_find_similar_entities_different_type(self):
        """Test that different entity types are not matched"""
        # Create a PERSON entity with similar name
        person_id = graph_service.create_or_merge_entity(
            name="Microsoft Person",
            entity_type="PERSON",
            description="A person",
            confidence=0.8,
        )

        similar = entity_resolution_service.find_similar_entities(
            entity_name="Microsoft Corporation",
            entity_type="ORGANIZATION",  # Looking for ORGANIZATION
            threshold=0.5,
        )

        # Should not find the PERSON entity
        names = [e["name"] for e in similar]
        assert "Microsoft Person" not in names

        # Cleanup
        session = graph_service.get_session()
        session.run("MATCH (e:Entity {id: $id}) DETACH DELETE e", id=person_id)


@pytest.mark.integration
class TestFindDuplicatePairs:
    """Integration tests for finding duplicate entity pairs"""

    @pytest.fixture(autouse=True)
    def setup_test_entities(self):
        """Create test entities before each test"""
        graph_service.init_schema()

        self.entity_ids = []

        # Create several similar entities
        self.entity_ids.append(graph_service.create_or_merge_entity(
            name="OpenAI",
            entity_type="ORGANIZATION",
            description="AI research company",
            confidence=0.9,
        ))

        self.entity_ids.append(graph_service.create_or_merge_entity(
            name="Open AI",
            entity_type="ORGANIZATION",
            description="AI company",
            confidence=0.85,
        ))

        self.entity_ids.append(graph_service.create_or_merge_entity(
            name="Google",
            entity_type="ORGANIZATION",
            description="Search engine",
            confidence=0.9,
        ))

        yield

        # Cleanup
        session = graph_service.get_session()
        for entity_id in self.entity_ids:
            session.run("MATCH (e:Entity {id: $id}) DETACH DELETE e", id=entity_id)

    def test_find_duplicate_pairs_success(self):
        """Test finding duplicate pairs"""
        pairs = entity_resolution_service.find_duplicate_entity_pairs(
            entity_type="ORGANIZATION",
            threshold=0.7,
        )

        # Should find at least the OpenAI / Open AI pair
        assert len(pairs) >= 1

        # Verify pair structure
        for entity1, entity2, similarity in pairs:
            assert "id" in entity1
            assert "name" in entity1
            assert "type" in entity1
            assert similarity >= 0.7

    def test_find_duplicate_pairs_filtered_by_type(self):
        """Test filtering by entity type"""
        # Create a PERSON entity
        person_id = graph_service.create_or_merge_entity(
            name="OpenAI Person",
            entity_type="PERSON",
            description="A person",
            confidence=0.8,
        )

        pairs = entity_resolution_service.find_duplicate_entity_pairs(
            entity_type="ORGANIZATION",
            threshold=0.5,
        )

        # All pairs should be ORGANIZATION type
        for entity1, entity2, _ in pairs:
            assert entity1["type"] == "ORGANIZATION"
            assert entity2["type"] == "ORGANIZATION"

        # Cleanup
        session = graph_service.get_session()
        session.run("MATCH (e:Entity {id: $id}) DETACH DELETE e", id=person_id)


@pytest.mark.integration
class TestEntityMerging:
    """Integration tests for merging entities"""

    @pytest.fixture(autouse=True)
    def setup_test_entities(self):
        """Create test entities and relationships"""
        graph_service.init_schema()

        # Create primary entity
        self.primary_id = graph_service.create_or_merge_entity(
            name="Amazon",
            entity_type="ORGANIZATION",
            description="E-commerce company",
            confidence=0.9,
        )

        # Create duplicate entity
        self.duplicate_id = graph_service.create_or_merge_entity(
            name="Amazon.com",
            entity_type="ORGANIZATION",
            description="Online retailer",
            confidence=0.85,
        )

        # Create a third entity to have relationships with
        self.related_id = graph_service.create_or_merge_entity(
            name="AWS",
            entity_type="TECHNOLOGY",
            description="Cloud platform",
            confidence=0.9,
        )

        # Create relationship from duplicate to related entity
        graph_service.create_relationship(
            source_entity_id=self.duplicate_id,
            target_entity_id=self.related_id,
            relationship_type="RELATED_TO",
            description="Amazon provides AWS",
            confidence=0.9,
        )

        yield

        # Cleanup
        session = graph_service.get_session()
        session.run(
            "MATCH (e:Entity) WHERE e.id IN [$id1, $id2, $id3] DETACH DELETE e",
            id1=self.primary_id, id2=self.duplicate_id, id3=self.related_id
        )

    def test_merge_entities_success(self):
        """Test successful entity merge"""
        result = entity_resolution_service.merge_entities(
            primary_entity_id=self.primary_id,
            duplicate_entity_ids=[self.duplicate_id],
            canonical_name="Amazon",
        )

        assert result["status"] == "success"
        assert result["merged_count"] == 1
        assert "Amazon.com" in result["aliases"]

        # Verify duplicate entity is deleted
        session = graph_service.get_session()
        check_result = session.run(
            "MATCH (e:Entity {id: $id}) RETURN e",
            id=self.duplicate_id
        )
        assert check_result.single() is None

        # Verify primary entity still exists
        check_result = session.run(
            "MATCH (e:Entity {id: $id}) RETURN e.name as name, e.aliases as aliases",
            id=self.primary_id
        )
        record = check_result.single()
        assert record is not None
        assert record["name"] == "Amazon"
        assert "Amazon.com" in (record["aliases"] or [])

    def test_merge_entities_transfers_relationships(self):
        """Test that relationships are transferred during merge"""
        result = entity_resolution_service.merge_entities(
            primary_entity_id=self.primary_id,
            duplicate_entity_ids=[self.duplicate_id],
        )

        assert result["status"] == "success"

        # Verify relationship now connects primary entity to related entity
        session = graph_service.get_session()
        check_result = session.run(
            """
            MATCH (primary:Entity {id: $primary_id})-[r]->(related:Entity {id: $related_id})
            RETURN type(r) as rel_type
            """,
            primary_id=self.primary_id,
            related_id=self.related_id
        )
        record = check_result.single()
        assert record is not None

    def test_merge_entities_invalid_primary(self):
        """Test merge with invalid primary entity"""
        result = entity_resolution_service.merge_entities(
            primary_entity_id="invalid_id_12345",
            duplicate_entity_ids=[self.duplicate_id],
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


@pytest.mark.integration
class TestEntityAliases:
    """Integration tests for entity alias management"""

    @pytest.fixture(autouse=True)
    def setup_test_entity(self):
        """Create test entity"""
        graph_service.init_schema()

        self.entity_id = graph_service.create_or_merge_entity(
            name="Tesla",
            entity_type="ORGANIZATION",
            description="Electric vehicle company",
            confidence=0.9,
        )

        yield

        # Cleanup
        session = graph_service.get_session()
        session.run("MATCH (e:Entity {id: $id}) DETACH DELETE e", id=self.entity_id)

    def test_add_alias_success(self):
        """Test adding alias to entity"""
        success = entity_resolution_service.add_entity_alias(
            entity_id=self.entity_id,
            alias="Tesla Motors"
        )

        assert success is True

        # Verify alias was added
        aliases = entity_resolution_service.get_entity_aliases(self.entity_id)
        assert "Tesla Motors" in aliases

    def test_add_duplicate_alias(self):
        """Test adding same alias twice (should not duplicate)"""
        entity_resolution_service.add_entity_alias(
            entity_id=self.entity_id,
            alias="Tesla Inc"
        )

        entity_resolution_service.add_entity_alias(
            entity_id=self.entity_id,
            alias="Tesla Inc"
        )

        # Should only appear once
        aliases = entity_resolution_service.get_entity_aliases(self.entity_id)
        assert aliases.count("Tesla Inc") == 1

    def test_get_aliases_includes_canonical_name(self):
        """Test that get_aliases returns canonical name + aliases"""
        entity_resolution_service.add_entity_alias(
            entity_id=self.entity_id,
            alias="Tesla Motors"
        )

        aliases = entity_resolution_service.get_entity_aliases(self.entity_id)

        # Should include canonical name
        assert "Tesla" in aliases
        # Should include alias
        assert "Tesla Motors" in aliases


@pytest.mark.integration
class TestEntityResolutionEndpoints:
    """Integration tests for entity resolution API endpoints"""

    @pytest.fixture(autouse=True)
    def setup_test_entities(self):
        """Create test entities for API testing"""
        graph_service.init_schema()

        self.entity1_id = graph_service.create_or_merge_entity(
            name="Netflix",
            entity_type="ORGANIZATION",
            description="Streaming service",
            confidence=0.9,
        )

        self.entity2_id = graph_service.create_or_merge_entity(
            name="Netflix Inc",
            entity_type="ORGANIZATION",
            description="Media company",
            confidence=0.85,
        )

        yield

        # Cleanup
        session = graph_service.get_session()
        session.run(
            "MATCH (e:Entity) WHERE e.id IN [$id1, $id2] DETACH DELETE e",
            id1=self.entity1_id, id2=self.entity2_id
        )

    def test_find_similar_entities_endpoint(self, authenticated_client):
        """Test find similar entities API endpoint"""
        response = authenticated_client.post(
            "/api/admin/entity-resolution/find-similar",
            json={
                "entity_name": "Netflix",
                "entity_type": "ORGANIZATION",
                "threshold": 0.7,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "similar_entities" in data
        assert data["count"] >= 0

    def test_find_duplicates_endpoint(self, authenticated_client):
        """Test find duplicates API endpoint"""
        response = authenticated_client.post(
            "/api/admin/entity-resolution/find-duplicates",
            json={
                "entity_type": "ORGANIZATION",
                "threshold": 0.7,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "duplicate_pairs" in data
        assert "threshold" in data

    def test_add_alias_endpoint(self, authenticated_client):
        """Test add alias API endpoint"""
        response = authenticated_client.post(
            "/api/admin/entity-resolution/add-alias",
            json={
                "entity_id": self.entity1_id,
                "alias": "Netflix Streaming"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Netflix Streaming" in data["all_aliases"]

    def test_get_aliases_endpoint(self, authenticated_client):
        """Test get aliases API endpoint"""
        # Add an alias first
        entity_resolution_service.add_entity_alias(
            entity_id=self.entity1_id,
            alias="NFLX"
        )

        response = authenticated_client.get(
            f"/api/admin/entity-resolution/aliases/{self.entity1_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["canonical_name"] == "Netflix"
        assert "NFLX" in data["aliases"]

    def test_merge_entities_endpoint(self, authenticated_client):
        """Test merge entities API endpoint"""
        response = authenticated_client.post(
            "/api/admin/entity-resolution/merge",
            json={
                "primary_entity_id": self.entity1_id,
                "duplicate_entity_ids": [self.entity2_id],
                "canonical_name": "Netflix"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["merged_count"] >= 1
        assert "Netflix Inc" in data["aliases"]
