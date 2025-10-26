"""
Graph visualization service for preparing data for frontend visualization
Exports data in Cytoscape.js format
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.db.neo4j import get_neo4j_session

logger = logging.getLogger(__name__)


class VisualizationService:
    """Service for graph visualization data preparation"""

    def __init__(self):
        """Initialize visualization service"""
        self.session = None

    def get_session(self):
        """Get or create Neo4j session"""
        if not self.session:
            self.session = get_neo4j_session()
        return self.session

    def get_entity_graph(
        self, limit: int = 100, include_communities: bool = True
    ) -> Dict[str, Any]:
        """
        Get entity graph for visualization

        Args:
            limit: Maximum number of entities to include
            include_communities: Whether to include community nodes

        Returns:
            Dictionary with nodes and edges for Cytoscape.js
        """
        try:
            session = self.get_session()

            # Get entities
            entity_query = f"""
            MATCH (e:Entity)
            OPTIONAL MATCH (e)-[r:IN_COMMUNITY]->(c:Community)
            RETURN
                e.id AS id,
                e.name AS label,
                e.type AS type,
                e.description AS description,
                c.id AS community_id
            LIMIT {limit}
            """

            entities = session.run(entity_query).data()

            # Get relationships
            rel_query = """
            MATCH (e1:Entity)-[r]-(e2:Entity)
            WHERE e1.id IN $entity_ids AND e2.id IN $entity_ids
            RETURN
                e1.id AS source,
                e2.id AS target,
                type(r) AS type,
                r.description AS description,
                r.confidence AS confidence
            """

            entity_ids = [e["id"] for e in entities]

            relationships = session.run(rel_query, {"entity_ids": entity_ids}).data()

            # Convert to Cytoscape format
            nodes = []
            for entity in entities:
                node = {
                    "data": {
                        "id": entity["id"],
                        "label": entity["label"],
                        "type": entity["type"],
                        "description": entity["description"] or "",
                        "community_id": entity.get("community_id"),
                    },
                    "classes": f"entity {entity['type'].lower()}",
                    "style": self._get_node_style(entity["type"]),
                }
                nodes.append(node)

            edges = []
            for rel in relationships:
                edge = {
                    "data": {
                        "id": f"{rel['source']}-{rel['target']}",
                        "source": rel["source"],
                        "target": rel["target"],
                        "label": rel["type"],
                        "description": rel.get("description", ""),
                        "confidence": rel.get("confidence", 0.5),
                    },
                    "classes": f"relationship {rel['type'].lower()}",
                }
                edges.append(edge)

            return {
                "status": "success",
                "node_count": len(nodes),
                "edge_count": len(edges),
                "elements": nodes + edges,
            }

        except Exception as e:
            logger.error(f"Failed to get entity graph: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_community_graph(
        self, include_members: bool = True, max_members: int = 10
    ) -> Dict[str, Any]:
        """
        Get community graph for visualization

        Args:
            include_members: Whether to include entity members in nodes
            max_members: Maximum members per community to show

        Returns:
            Dictionary with nodes and edges for Cytoscape.js
        """
        try:
            session = self.get_session()

            # Get communities
            community_query = """
            MATCH (c:Community)
            OPTIONAL MATCH (e:Entity)-[r:IN_COMMUNITY]->(c)
            RETURN
                c.id AS id,
                count(DISTINCT e) AS size,
                c.summary AS summary,
                c.key_themes AS themes
            """

            communities = session.run(community_query).data()

            # Get inter-community connections
            connection_query = """
            MATCH (c1:Community)<-[r1:IN_COMMUNITY]-(e1:Entity)
            MATCH (e2:Entity)-[r2:IN_COMMUNITY]->(c2:Community)
            WHERE c1 <> c2 AND (e1)-[rel]-(e2)
            RETURN
                c1.id AS source_community,
                c2.id AS target_community,
                count(rel) AS connection_count,
                collect(DISTINCT type(rel)) AS relationship_types
            """

            connections = session.run(connection_query).data()

            # Convert to Cytoscape format
            nodes = []
            for community in communities:
                node = {
                    "data": {
                        "id": f"community_{community['id']}",
                        "label": f"Community {community['id']}",
                        "size": community["size"],
                        "summary": community.get("summary", "")[:100],
                        "themes": community.get("themes", "").split(",") if community.get("themes") else [],
                    },
                    "classes": "community",
                    "style": {
                        "background-color": self._get_community_color(community["id"]),
                        "width": min(100, 50 + community["size"] * 5),
                        "height": min(100, 50 + community["size"] * 5),
                    },
                }
                nodes.append(node)

            edges = []
            for conn in connections:
                edge = {
                    "data": {
                        "id": f"community_{conn['source_community']}-community_{conn['target_community']}",
                        "source": f"community_{conn['source_community']}",
                        "target": f"community_{conn['target_community']}",
                        "label": f"{conn['connection_count']} connections",
                        "connection_count": conn["connection_count"],
                        "relationship_types": conn.get("relationship_types", []),
                    },
                    "classes": "community-connection",
                }
                edges.append(edge)

            return {
                "status": "success",
                "community_count": len(nodes),
                "connection_count": len(edges),
                "elements": nodes + edges,
            }

        except Exception as e:
            logger.error(f"Failed to get community graph: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_hierarchical_graph(self) -> Dict[str, Any]:
        """
        Get hierarchical graph (documents -> textunits -> entities -> communities)

        Returns:
            Dictionary with hierarchical graph data
        """
        try:
            session = self.get_session()

            # Get documents
            doc_query = """
            MATCH (d:Document)
            RETURN d.id AS id, d.filename AS label, count(d) AS count
            """

            documents = session.run(doc_query).data()

            # Get relationships at different levels
            doc_to_textunit = """
            MATCH (d:Document)-[r:CONTAINS]->(tu:TextUnit)
            RETURN d.id AS source, tu.id AS target, type(r) AS type
            LIMIT 50
            """

            doc_rels = session.run(doc_to_textunit).data()

            textunit_to_entity = """
            MATCH (tu:TextUnit)-[r:CONTAINS_ENTITY]->(e:Entity)
            RETURN tu.id AS source, e.id AS target, type(r) AS type
            LIMIT 50
            """

            tu_rels = session.run(textunit_to_entity).data()

            # Build nodes
            nodes = []

            # Document nodes
            for doc in documents:
                nodes.append({
                    "data": {
                        "id": f"doc_{doc['id']}",
                        "label": doc["label"] or f"Doc {doc['id']}",
                        "type": "document",
                    },
                    "classes": "document",
                })

            # Build edges
            edges = []
            for rel in doc_rels + tu_rels:
                edges.append({
                    "data": {
                        "source": rel["source"],
                        "target": rel["target"],
                        "label": rel["type"],
                    }
                })

            return {
                "status": "success",
                "node_count": len(nodes),
                "edge_count": len(edges),
                "elements": nodes + edges,
            }

        except Exception as e:
            logger.error(f"Failed to get hierarchical graph: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_ego_graph(
        self, entity_id: str, hop_limit: int = 2
    ) -> Dict[str, Any]:
        """
        Get ego graph centered on a specific entity

        Args:
            entity_id: Entity ID
            hop_limit: Number of hops to include

        Returns:
            Dictionary with ego graph data
        """
        try:
            session = self.get_session()

            # Get central entity
            entity_query = """
            MATCH (e:Entity {id: $entity_id})
            RETURN e.id AS id, e.name AS label, e.type AS type
            """

            central = session.run(entity_query, {"entity_id": entity_id}).single()

            if not central:
                return {"status": "not_found", "entity_id": entity_id}

            # Get neighbors
            neighbor_query = f"""
            MATCH (e:Entity {{id: $entity_id}})
            MATCH (e)-[r*1..{hop_limit}]-(neighbor:Entity)
            RETURN
                neighbor.id AS id,
                neighbor.name AS label,
                neighbor.type AS type,
                length(path) AS distance
            """

            neighbors = session.run(neighbor_query, {"entity_id": entity_id}).data()

            # Get relationships
            rel_query = f"""
            MATCH (e:Entity {{id: $entity_id}})
            MATCH path = (e)-[r*1..{hop_limit}]-(neighbor:Entity)
            RETURN
                e.id AS source,
                neighbor.id AS target,
                [rel in relationships(path) | type(rel)] AS types
            """

            relationships = session.run(rel_query, {"entity_id": entity_id}).data()

            # Build nodes
            nodes = []
            nodes.append({
                "data": {
                    "id": central["id"],
                    "label": central["label"],
                    "type": central["type"],
                },
                "classes": "central-entity",
            })

            for neighbor in neighbors:
                nodes.append({
                    "data": {
                        "id": neighbor["id"],
                        "label": neighbor["label"],
                        "type": neighbor["type"],
                        "distance": neighbor["distance"],
                    },
                    "classes": f"neighbor distance-{neighbor['distance']}",
                })

            # Build edges
            edges = []
            for rel in relationships:
                edges.append({
                    "data": {
                        "id": f"{rel['source']}-{rel['target']}",
                        "source": rel["source"],
                        "target": rel["target"],
                        "label": ",".join(rel.get("types", [])),
                    }
                })

            return {
                "status": "success",
                "central_entity": central["label"],
                "node_count": len(nodes),
                "edge_count": len(edges),
                "elements": nodes + edges,
            }

        except Exception as e:
            logger.error(f"Failed to get ego graph: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _get_node_style(self, entity_type: str) -> Dict[str, Any]:
        """Get visual style for node based on entity type"""
        colors = {
            "PERSON": "#FF6B6B",
            "ORGANIZATION": "#4ECDC4",
            "LOCATION": "#45B7D1",
            "CONCEPT": "#96CEB4",
            "EVENT": "#FFEAA7",
            "PRODUCT": "#DDA15E",
            "OTHER": "#C9ADA7",
        }
        return {
            "background-color": colors.get(entity_type, "#999999"),
            "width": "50px",
            "height": "50px",
        }

    def _get_community_color(self, community_id: int) -> str:
        """Generate color for community based on ID"""
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
            "#DDA15E", "#BC6C25", "#9D4EDD", "#5A189A", "#3C096C"
        ]
        return colors[community_id % len(colors)]


# Singleton instance
visualization_service = VisualizationService()
