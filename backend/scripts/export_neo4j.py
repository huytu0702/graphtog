import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from neo4j import GraphDatabase


def serialize_default(obj: Any) -> Any:
    """Fallback serializer to handle Neo4j/UUID/Date types."""
    try:
        return str(obj)
    except Exception:
        return None


def fetch_nodes(session) -> List[Dict[str, Any]]:
    query = """
    MATCH (n)
    RETURN id(n) AS id, labels(n) AS labels, properties(n) AS properties
    ORDER BY id(n)
    """
    result = session.run(query)
    nodes = []
    for record in result:
        nodes.append(
            {
                "id": record["id"],
                "labels": record["labels"],
                "properties": record["properties"],
            }
        )
    return nodes


def fetch_relationships(session) -> List[Dict[str, Any]]:
    query = """
    MATCH (a)-[r]->(b)
    RETURN id(r) AS id, type(r) AS type, id(a) AS start, id(b) AS end, properties(r) AS properties
    ORDER BY id(r)
    """
    result = session.run(query)
    relationships = []
    for record in result:
        relationships.append(
            {
                "id": record["id"],
                "type": record["type"],
                "start": record["start"],
                "end": record["end"],
                "properties": record["properties"],
            }
        )
    return relationships


def fetch_schema_stats(session) -> Dict[str, Any]:
    labels_res = session.run("CALL db.labels()")
    labels = [r["label"] for r in labels_res]

    reltypes_res = session.run("CALL db.relationshipTypes()")
    reltypes = [r["relationshipType"] for r in reltypes_res]

    node_count_res = session.run("MATCH (n) RETURN count(n) AS c")
    node_count_rec = node_count_res.single()
    node_count = node_count_rec["c"] if node_count_rec else 0

    rel_count_res = session.run("MATCH ()-[r]->() RETURN count(r) AS c")
    rel_count_rec = rel_count_res.single()
    rel_count = rel_count_rec["c"] if rel_count_rec else 0

    return {
        "labels": labels,
        "relationshipTypes": reltypes,
        "nodeCount": node_count,
        "relationshipCount": rel_count,
    }


def export_neo4j(uri: str, user: str, password: str, out_path: str) -> str:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            nodes = fetch_nodes(session)
            relationships = fetch_relationships(session)
            stats = fetch_schema_stats(session)

        export = {
            "meta": {
                "exportedAt": datetime.utcnow().isoformat() + "Z",
                "uri": uri,
                "user": user,
                "tool": "export_neo4j.py",
                "version": 1,
            },
            "stats": stats,
            "nodes": nodes,
            "relationships": relationships,
        }

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2, default=serialize_default)

        return out_path
    finally:
        driver.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Neo4j graph to JSON.")
    parser.add_argument(
        "--uri",
        default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j Bolt URI (default: bolt://localhost:7687)",
    )
    parser.add_argument(
        "--user",
        default=os.getenv("NEO4J_USER", "neo4j"),
        help="Neo4j username (default: neo4j)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("NEO4J_PASSWORD", "graphtog_password"),
        help="Neo4j password (default: graphtog_password)",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "neo4j_dump.json"),
        help="Output JSON file path (default: project_root/neo4j_dump.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        out_path = os.path.abspath(args.out)
        exported = export_neo4j(args.uri, args.user, args.password, out_path)
        print(f"Exported Neo4j graph to: {exported}")
    except Exception as e:
        print(f"Failed to export Neo4j graph: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


