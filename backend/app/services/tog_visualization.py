"""
ToG Reasoning Path Visualization Service.

Generates visualization data (nodes, edges, metadata) for displaying ToG reasoning paths
in frontend components like graph visualizations or reasoning trees.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class ToGVisualizationService:
    """Service for generating visualization data from ToG reasoning paths."""

    def __init__(self):
        pass

    def generate_visualization_data(
        self,
        reasoning_path: Any,  # ToGReasoningPath
        question: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive visualization data from a ToG reasoning path.

        Args:
            reasoning_path: ToGReasoningPath object with steps and triplets
            question: Original question for context

        Returns:
            Dictionary with nodes, edges, and metadata for visualization
        """
        try:
            # Extract all entities and relations from reasoning path
            entities = self._extract_entities_from_path(reasoning_path)
            relations = self._extract_relations_from_path(reasoning_path)

            # Generate visualization nodes and edges
            nodes = self._create_visualization_nodes(entities, reasoning_path)
            edges = self._create_visualization_edges(relations, reasoning_path)

            # Generate metadata
            metadata = self._create_visualization_metadata(
                reasoning_path, question, len(nodes), len(edges)
            )

            # Generate layout hints
            layout = self._generate_layout_hints(nodes, edges, reasoning_path)

            return {
                "nodes": nodes,
                "edges": edges,
                "metadata": metadata,
                "layout": layout,
                "question": question
            }

        except Exception as e:
            logger.error(f"Failed to generate visualization data: {e}")
            return self._create_error_visualization(question, str(e))

    def _extract_entities_from_path(self, reasoning_path) -> List[Dict[str, Any]]:
        """Extract all unique entities from reasoning path."""
        entities = {}

        # Extract from reasoning steps
        for step in reasoning_path.steps:
            for entity in step.entities_explored:
                entity_key = entity.id
                if entity_key not in entities:
                    entities[entity_key] = {
                        "id": entity.id,
                        "name": entity.name,
                        "type": entity.type,
                        "description": entity.description,
                        "confidence": entity.confidence,
                        "first_seen_depth": step.depth,
                        "document_id": entity.document_id
                    }

        # Extract from triplets (in case some entities aren't in steps)
        if hasattr(reasoning_path, 'retrieved_triplets'):
            for triplet in reasoning_path.retrieved_triplets:
                # Create placeholder entities for subjects/objects not in steps
                for entity_name in [triplet.subject, triplet.object]:
                    entity_key = f"triplet_{entity_name}"
                    if entity_key not in entities:
                        entities[entity_key] = {
                            "id": entity_key,
                            "name": entity_name,
                            "type": "UNKNOWN",
                            "description": f"Entity from triplet: {entity_name}",
                            "confidence": triplet.confidence,
                            "first_seen_depth": 0,
                            "document_id": None
                        }

        return list(entities.values())

    def _extract_relations_from_path(self, reasoning_path) -> List[Dict[str, Any]]:
        """Extract all relations from reasoning path."""
        relations = []

        # Extract from triplets
        if hasattr(reasoning_path, 'retrieved_triplets'):
            for triplet in reasoning_path.retrieved_triplets:
                relations.append({
                    "source": triplet.subject,
                    "target": triplet.object,
                    "type": triplet.relation,
                    "confidence": triplet.confidence,
                    "source_step": triplet.source or "unknown",
                    "id": f"{triplet.subject}_{triplet.relation}_{triplet.object}"
                })

        # Extract from reasoning steps
        for step in reasoning_path.steps:
            for relation in step.relations_selected:
                # Check if this relation is already in triplets
                existing = any(
                    r["source"] == relation.source_entity.name and
                    r["target"] == relation.target_entity.name and
                    r["type"] == relation.type
                    for r in relations
                )

                if not existing:
                    relations.append({
                        "source": relation.source_entity.name,
                        "target": relation.target_entity.name,
                        "type": relation.type,
                        "confidence": relation.confidence,
                        "source_step": f"depth_{step.depth}",
                        "id": f"{relation.source_entity.name}_{relation.type}_{relation.target_entity.name}"
                    })

        return relations

    def _create_visualization_nodes(
        self, entities: List[Dict[str, Any]], reasoning_path
    ) -> List[Dict[str, Any]]:
        """Create visualization nodes with styling and positioning hints."""
        nodes = []

        # Group entities by depth for coloring/layout
        depth_groups = defaultdict(list)
        for entity in entities:
            depth = entity.get("first_seen_depth", 0)
            depth_groups[depth].append(entity)

        # Color scheme based on depth
        depth_colors = [
            "#4CAF50",  # Green - starting entities
            "#2196F3",  # Blue - depth 1
            "#FF9800",  # Orange - depth 2
            "#F44336",  # Red - depth 3
            "#9C27B0",  # Purple - deeper
        ]

        for entity in entities:
            depth = entity.get("first_seen_depth", 0)
            color = depth_colors[min(depth, len(depth_colors) - 1)]

            # Size based on confidence and type
            base_size = 20
            confidence_boost = entity.get("confidence", 0.5) * 10
            size = base_size + confidence_boost

            # Shape based on entity type
            shape = "circle"
            if entity.get("type") == "PERSON":
                shape = "circle"
            elif entity.get("type") == "ORGANIZATION":
                shape = "square"
            elif entity.get("type") in ["GEO", "LOCATION"]:
                shape = "triangle"
            elif entity.get("type") == "EVENT":
                shape = "diamond"

            node = {
                "id": entity["id"],
                "label": entity["name"],
                "type": entity.get("type", "UNKNOWN"),
                "description": entity.get("description", ""),
                "confidence": entity.get("confidence", 0.5),
                "depth": depth,
                "document_id": entity.get("document_id"),

                # Visualization properties
                "color": color,
                "size": size,
                "shape": shape,
                "group": f"depth_{depth}",

                # Positioning hints
                "x": None,  # Will be set by layout algorithm
                "y": None,

                # Interaction properties
                "clickable": True,
                "draggable": True,
                "hoverable": True
            }

            nodes.append(node)

        return nodes

    def _create_visualization_edges(
        self, relations: List[Dict[str, Any]], reasoning_path
    ) -> List[Dict[str, Any]]:
        """Create visualization edges with styling."""
        edges = []

        for relation in relations:
            # Map entity names to node IDs
            source_id = None
            target_id = None

            # Find matching node IDs
            for node in []:  # We'll get nodes from the parent function
                pass

            # For now, create IDs based on names (will be resolved later)
            source_id = f"entity_{relation['source'].replace(' ', '_')}"
            target_id = f"entity_{relation['target'].replace(' ', '_')}"

            # Edge styling based on confidence
            confidence = relation.get("confidence", 0.5)
            if confidence > 0.8:
                width = 3
                color = "#4CAF50"
            elif confidence > 0.6:
                width = 2
                color = "#FF9800"
            else:
                width = 1
                color = "#F44336"

            # Style based on relation type
            edge_type = "solid"
            if "similar" in relation["type"].lower() or "related" in relation["type"].lower():
                edge_type = "dashed"

            edge = {
                "id": relation["id"],
                "source": source_id,
                "target": target_id,
                "label": relation["type"],
                "confidence": confidence,
                "source_step": relation.get("source_step", "unknown"),

                # Visualization properties
                "color": color,
                "width": width,
                "type": edge_type,
                "curved": True,

                # Interaction properties
                "clickable": True,
                "hoverable": True
            }

            edges.append(edge)

        return edges

    def _create_visualization_metadata(
        self, reasoning_path, question: str, node_count: int, edge_count: int
    ) -> Dict[str, Any]:
        """Create metadata for the visualization."""
        return {
            "question": question,
            "total_steps": len(reasoning_path.steps),
            "max_depth": max((s.depth for s in reasoning_path.steps), default=0),
            "node_count": node_count,
            "edge_count": edge_count,
            "final_answer": reasoning_path.final_answer,
            "confidence_score": reasoning_path.confidence_score,
            "sufficiency_status": reasoning_path.sufficiency_status,

            # Statistics
            "statistics": {
                "entities_explored": sum(len(s.entities_explored) for s in reasoning_path.steps),
                "relations_selected": sum(len(s.relations_selected) for s in reasoning_path.steps),
                "avg_sufficiency_score": sum(
                    s.sufficiency_score or 0 for s in reasoning_path.steps
                ) / max(len(reasoning_path.steps), 1)
            },

            # Visualization settings
            "settings": {
                "show_confidence": True,
                "show_depth_colors": True,
                "animate_steps": True,
                "layout_algorithm": "force_directed"
            }
        }

    def _generate_layout_hints(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], reasoning_path
    ) -> Dict[str, Any]:
        """Generate layout hints for better visualization."""
        # Group nodes by depth for hierarchical layout
        depth_groups = defaultdict(list)
        for node in nodes:
            depth_groups[node["depth"]].append(node)

        # Calculate positions for hierarchical layout
        layout = {
            "type": "hierarchical",
            "direction": "left_to_right",
            "level_separation": 200,
            "node_separation": 100,

            "depth_levels": {}
        }

        # Position nodes by depth
        y_start = 100
        for depth, depth_nodes in depth_groups.items():
            layout["depth_levels"][depth] = {
                "y": y_start + (depth * 150),
                "nodes": [node["id"] for node in depth_nodes]
            }

        return layout

    def _create_error_visualization(self, question: str, error: str) -> Dict[str, Any]:
        """Create a basic visualization for error cases."""
        return {
            "nodes": [{
                "id": "error_node",
                "label": "Error",
                "type": "ERROR",
                "description": f"Visualization failed: {error}",
                "color": "#F44336",
                "size": 30,
                "shape": "circle"
            }],
            "edges": [],
            "metadata": {
                "question": question,
                "error": error,
                "total_steps": 0,
                "node_count": 1,
                "edge_count": 0
            },
            "layout": {
                "type": "single_node"
            }
        }

    def generate_step_by_step_animation(
        self, reasoning_path, question: str
    ) -> List[Dict[str, Any]]:
        """
        Generate step-by-step animation frames for visualizing the reasoning process.

        Returns:
            List of animation frames, each containing nodes/edges visible at that step
        """
        frames = []

        # Frame 0: Initial question
        frames.append({
            "step": 0,
            "description": f"Question: {question}",
            "nodes": [],
            "edges": [],
            "highlight": None
        })

        current_nodes = set()
        current_edges = set()

        for step_idx, step in enumerate(reasoning_path.steps):
            frame_nodes = []
            frame_edges = []

            # Add entities from this step
            for entity in step.entities_explored:
                if entity.id not in current_nodes:
                    current_nodes.add(entity.id)
                    frame_nodes.append({
                        "id": entity.id,
                        "highlight": "new",
                        "animation": "fade_in"
                    })

            # Add relations from this step
            for relation in step.relations_selected:
                edge_id = f"{relation.source_entity.id}_{relation.type}_{relation.target_entity.id}"
                if edge_id not in current_edges:
                    current_edges.add(edge_id)
                    frame_edges.append({
                        "id": edge_id,
                        "highlight": "new",
                        "animation": "draw"
                    })

            frames.append({
                "step": step_idx + 1,
                "description": f"Depth {step.depth}: Exploring {len(step.entities_explored)} entities",
                "nodes": frame_nodes,
                "edges": frame_edges,
                "sufficiency_score": step.sufficiency_score,
                "reasoning_notes": step.reasoning_notes
            })

        return frames
