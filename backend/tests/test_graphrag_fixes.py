"""
Test script to validate GraphRAG critical fixes
Tests hierarchical communities, community summaries, and global search
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.neo4j import get_neo4j_session
from app.services.community_detection import community_detection_service
from app.services.community_summarization import community_summarization_service
from app.services.retrieval_service import retrieval_service


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def test_hierarchical_communities():
    """Test hierarchical community storage"""
    print_section("🧪 Test 1: Hierarchical Community Storage")
    
    try:
        session = get_neo4j_session()
        
        # Check if hierarchical communities exist
        query = """
        MATCH (c:Community)
        RETURN 
            c.id AS community_id, 
            c.level AS level, 
            count(c) AS count
        ORDER BY c.level
        LIMIT 10
        """
        
        results = session.run(query).data()
        
        if not results:
            print("❌ FAILED: No communities found in database")
            return False
        
        print(f"✅ Found {len(results)} communities with hierarchy info:")
        
        # Group by level
        levels = {}
        for result in results:
            level = result.get("level", 0)
            if level not in levels:
                levels[level] = 0
            levels[level] += 1
        
        for level in sorted(levels.keys()):
            print(f"   • Level {level}: {levels[level]} communities")
        
        # Check if relationships have community_level property
        rel_query = """
        MATCH (e:Entity)-[r:IN_COMMUNITY]->(c:Community)
        WHERE r.community_level IS NOT NULL
        RETURN count(r) AS rel_count
        LIMIT 1
        """
        
        rel_result = session.run(rel_query).single()
        if rel_result and rel_result["rel_count"] > 0:
            print(f"   ✅ Relationships have community_level property ({rel_result['rel_count']} found)")
        else:
            print("   ⚠️  No relationships with community_level property found")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


async def test_community_summaries():
    """Test community summary generation and storage"""
    print_section("🧪 Test 2: Community Summary Generation")
    
    try:
        session = get_neo4j_session()
        
        # Check existing summaries first
        check_query = """
        MATCH (c:Community)
        WHERE c.summary IS NOT NULL AND c.summary <> ""
        RETURN count(c) AS summaries_count
        """
        
        check_result = session.run(check_query).single()
        existing_summaries = check_result["summaries_count"] if check_result else 0
        
        print(f"📊 Existing summaries: {existing_summaries}")
        
        # Generate summaries if needed
        if existing_summaries == 0:
            print("🔄 Generating community summaries...")
            results = community_summarization_service.summarize_all_communities()
            
            if results["status"] == "success":
                print(f"✅ Generated {results.get('num_communities_summarized', 0)} summaries")
                print(f"⚠️  Failed: {results.get('failed', 0)}")
            else:
                print(f"❌ FAILED: {results.get('message', 'Unknown error')}")
                return False
        
        # Verify stored summaries
        verify_query = """
        MATCH (c:Community)
        WHERE c.summary IS NOT NULL AND c.summary <> ""
        RETURN 
            c.id AS community_id,
            c.summary AS summary,
            c.key_themes AS themes,
            c.significance AS significance
        LIMIT 5
        """
        
        summaries = session.run(verify_query).data()
        
        if not summaries:
            print("❌ FAILED: No summaries found after generation")
            return False
        
        print(f"\n✅ Stored {len(summaries)} community summaries (showing first 3):")
        
        for i, s in enumerate(summaries[:3], 1):
            print(f"\n   Community {s['community_id']}:")
            summary_text = s.get('summary', 'N/A')
            print(f"   • Summary: {summary_text[:100]}..." if len(summary_text) > 100 else f"   • Summary: {summary_text}")
            print(f"   • Themes: {s.get('themes', 'N/A')}")
            print(f"   • Significance: {s.get('significance', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_global_search():
    """Test global search with community summaries"""
    print_section("🧪 Test 3: Global Search with Summaries")
    
    try:
        # Test global retrieval
        results = retrieval_service.retrieve_global_context(use_summaries=True)
        
        if results.get("status") != "success":
            print(f"❌ FAILED: {results.get('message', 'Unknown error')}")
            return False
        
        print(f"✅ Global search successful:")
        print(f"   • Communities: {results.get('num_communities', 0)}")
        print(f"   • Total entities: {results.get('total_entities', 0)}")
        print(f"   • Summaries available: {results.get('summaries_available', False)}")
        
        communities = results.get("communities", [])
        if communities:
            print(f"\n   First 3 communities:")
            for comm in communities[:3]:
                print(f"\n   Community {comm.get('community_id')}:")
                print(f"   • Size: {comm.get('size', 0)} entities")
                print(f"   • Level: {comm.get('level', 0)}")
                summary = comm.get('summary', 'N/A')
                print(f"   • Summary: {summary[:80]}..." if len(summary) > 80 else f"   • Summary: {summary}")
                themes = comm.get('themes', '')
                if themes:
                    print(f"   • Themes: {themes}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_graph_statistics():
    """Test overall graph statistics"""
    print_section("📊 Graph Statistics")
    
    try:
        session = get_neo4j_session()
        
        stats_query = """
        MATCH (e:Entity)
        WITH count(e) AS entity_count
        MATCH (c:Community)
        WITH entity_count, count(c) AS community_count
        MATCH (d:Document)
        WITH entity_count, community_count, count(d) AS document_count
        MATCH ()-[r:RELATED_TO]->()
        RETURN 
            entity_count,
            community_count,
            document_count,
            count(r) AS relationship_count
        """
        
        result = session.run(stats_query).single()
        
        if result:
            print(f"✅ Graph Statistics:")
            print(f"   • Documents: {result['document_count']}")
            print(f"   • Entities: {result['entity_count']}")
            print(f"   • Communities: {result['community_count']}")
            print(f"   • Relationships: {result['relationship_count']}")
            
            if result['entity_count'] == 0:
                print("\n⚠️  WARNING: No entities found. Please upload and process documents first.")
                return False
            
            if result['community_count'] == 0:
                print("\n⚠️  WARNING: No communities detected. Run community detection first.")
                return False
            
            return True
        else:
            print("❌ FAILED: Could not retrieve statistics")
            return False
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  🚀 GraphRAG Critical Fixes - Validation Tests")
    print("  Microsoft GraphRAG Methodology Implementation")
    print("=" * 70)
    
    results = {
        "statistics": False,
        "hierarchical_communities": False,
        "community_summaries": False,
        "global_search": False,
    }
    
    try:
        # Test 0: Graph statistics
        results["statistics"] = await test_graph_statistics()
        
        # Test 1: Hierarchical communities
        results["hierarchical_communities"] = await test_hierarchical_communities()
        
        # Test 2: Community summaries
        results["community_summaries"] = await test_community_summaries()
        
        # Test 3: Global search
        results["global_search"] = await test_global_search()
        
        # Summary
        print_section("📋 Test Summary")
        
        total_tests = len(results)
        passed_tests = sum(1 for v in results.values() if v)
        
        print(f"\nResults: {passed_tests}/{total_tests} tests passed\n")
        
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {status} - {test_name.replace('_', ' ').title()}")
        
        print("\n" + "=" * 70)
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! GraphRAG implementation is correct.")
            print("=" * 70 + "\n")
            return 0
        else:
            print("⚠️  Some tests failed. Please review the output above.")
            print("=" * 70 + "\n")
            return 1
    
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

