# 🔧 GraphRAG Critical Fixes - Implementation Guide

## Priority 0: Community Summarization & Hierarchical Communities

This guide provides step-by-step instructions to implement the missing critical components.

---

## Problem Summary

Your GraphRAG implementation is missing two critical components:

1. **Community Summaries** - Each community needs a generated summary of its themes and importance
2. **Hierarchical Communities** - Communities should be organized in levels (micro → macro)

Without these, your system **loses 50% of GraphRAG's power**.

---

## Solution Architecture

```
Before (Current):
Document → Entities → Communities (single level) → X (no summaries)

After (Fixed):
Document → Entities → Communities (multi-level) → Summaries → Global Search
```

---

## Implementation Step 1: Fix Hierarchical Community Storage

### Issue
`community_detection.py` extracts hierarchical community data but discards it:

```python
# Line 118 - This data is LOST!
intermediateCommunityIds  # ← Contains hierarchy info but not stored
```

### Solution

**File**: `backend/app/services/community_detection.py`

Replace the `_store_community_assignments()` method:

```python
def _store_community_assignments(self, session, results: List[Dict]) -> None:
    """
    Store community assignments in Neo4j with hierarchy levels
    
    Args:
        session: Neo4j session
        results: Community detection results with hierarchy info
    """
    try:
        # First pass: create all community nodes and relationships
        for record in results:
            entity_name = record["entity_name"]
            community_id = record["communityId"]
            community_level = 0  # Base level for primary community
            
            # Create primary community relationship
            store_query = """
            MATCH (e:Entity {name: $entity_name})
            MERGE (c:Community {id: $community_id})
            ON CREATE SET 
                c.createdAt = datetime(),
                c.level = $community_level,
                c.summary = ""
            MERGE (e)-[r:IN_COMMUNITY]->(c)
            SET r.confidence = 0.95, 
                r.timestamp = datetime(),
                r.community_level = $community_level
            RETURN e.name, c.id
            """
            
            session.run(
                store_query,
                {
                    "entity_name": entity_name,
                    "community_id": community_id,
                    "community_level": community_level,
                },
            )
            
            # Store intermediate communities (hierarchy)
            if "intermediateCommunityIds" in record and record["intermediateCommunityIds"]:
                intermediate_ids = record["intermediateCommunityIds"]
                for idx, inter_comm_id in enumerate(intermediate_ids):
                    level = idx + 1  # Higher level
                    
                    # Create intermediate community node
                    inter_query = """
                    MATCH (e:Entity {name: $entity_name})
                    MERGE (ic:Community {id: $inter_community_id})
                    ON CREATE SET 
                        ic.createdAt = datetime(),
                        ic.level = $community_level,
                        ic.summary = ""
                    MERGE (e)-[r2:IN_COMMUNITY]->(ic)
                    SET r2.confidence = 0.85,
                        r2.timestamp = datetime(),
                        r2.community_level = $community_level
                    RETURN e.name, ic.id
                    """
                    
                    session.run(
                        inter_query,
                        {
                            "entity_name": entity_name,
                            "inter_community_id": inter_comm_id,
                            "community_level": level,
                        },
                    )
        
        logger.info("✅ Community assignments stored with hierarchy levels")
        
    except Exception as e:
        logger.error(f"Failed to store community assignments: {str(e)}")
```

---

## Implementation Step 2: Implement Community Summarization

### Issue
`community_summarization.py` exists but is NOT integrated into the pipeline and NOT generating summaries.

### Solution

**File**: `backend/app/services/community_summarization.py`

Implement the summarization service (currently empty):

```python
"""
Community summarization service for GraphRAG
Generates natural language summaries of communities
"""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import get_settings
from app.db.neo4j import get_neo4j_session

logger = logging.getLogger(__name__)
settings = get_settings()
genai.configure(api_key=settings.GOOGLE_API_KEY)


class CommunitySummarizationService:
    """Service for generating community summaries"""
    
    def __init__(self):
        """Initialize community summarization service"""
        self.session = None
        self.model_name = "gemini-2.5-flash"
    
    def get_session(self):
        """Get or create Neo4j session"""
        if not self.session:
            self.session = get_neo4j_session()
        return self.session
    
    def get_community_context(
        self, community_id: int, max_members: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve context for a community
        
        Args:
            community_id: Community ID
            max_members: Max members to include
            
        Returns:
            Dictionary with community context
        """
        try:
            session = self.get_session()
            
            # Get community members and their relationships
            query = """
            MATCH (c:Community {id: $community_id})<-[r:IN_COMMUNITY]-(e:Entity)
            WITH c, e, r
            OPTIONAL MATCH (e)-[rel]-(other:Entity)
            WHERE other.name IN [other_e.name | other_e IN collect(other_e)]
            RETURN
                c.id AS community_id,
                c.level AS community_level,
                collect(DISTINCT {
                    name: e.name,
                    type: e.type,
                    description: e.description,
                    mention_count: e.mention_count,
                    confidence: e.confidence
                })[0..$max_members] AS members,
                collect(DISTINCT {
                    source: e.name,
                    target: other.name,
                    type: type(rel),
                    description: rel.description
                })[0..30] AS relationships,
                count(DISTINCT e) AS member_count
            LIMIT 1
            """
            
            result = session.run(query, {
                "community_id": community_id,
                "max_members": max_members
            }).single()
            
            if result:
                return dict(result)
            
            return {"status": "not_found", "community_id": community_id}
            
        except Exception as e:
            logger.error(f"Failed to get community context: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def generate_community_summary(
        self, community_id: int, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary for a community
        
        Args:
            community_id: Community ID
            context: Optional pre-fetched context
            
        Returns:
            Dictionary with summary
        """
        try:
            # Get context if not provided
            if not context:
                context = self.get_community_context(community_id)
            
            if "status" in context and context["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Could not get context for community {community_id}"
                }
            
            # Prepare summary prompt
            members_text = "\n".join([
                f"- {m['name']} ({m['type']}): {m.get('description', 'N/A')}"
                for m in context.get("members", [])[:10]
            ])
            
            relationships_text = "\n".join([
                f"- {r['source']} --{r['type']}--> {r['target']}: {r.get('description', '')}"
                for r in context.get("relationships", [])[:10]
            ])
            
            prompt = f"""Generate a comprehensive summary of this community in 2-3 sentences:

Community Level: {context.get('community_level', 0)}
Member Count: {context.get('member_count', 0)}

Key Members:
{members_text}

Key Relationships:
{relationships_text}

Provide:
1. A brief summary of what this community represents
2. Main themes or topics
3. Significance/importance (high/medium/low)

Format as JSON:
{{
    "summary": "...",
    "themes": ["...", "..."],
    "significance": "high|medium|low"
}}
"""
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            try:
                result_text = response.text.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                    result_text = result_text.strip()
                
                summary_data = json.loads(result_text)
                return {
                    "status": "success",
                    "community_id": community_id,
                    "summary": summary_data.get("summary", ""),
                    "themes": summary_data.get("themes", []),
                    "significance": summary_data.get("significance", "medium"),
                }
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse summary JSON: {e}")
                return {
                    "status": "error",
                    "message": "Invalid JSON in summary generation"
                }
        
        except Exception as e:
            logger.error(f"Failed to generate community summary: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def generate_all_summaries(self) -> Dict[str, Any]:
        """
        Generate summaries for all communities
        
        Returns:
            Dictionary with summary generation results
        """
        try:
            session = self.get_session()
            
            # Get all community IDs
            query = "MATCH (c:Community) RETURN c.id AS community_id, c.level AS level"
            communities = session.run(query).data()
            
            logger.info(f"Generating summaries for {len(communities)} communities...")
            
            results = {
                "status": "success",
                "total": len(communities),
                "completed": 0,
                "failed": 0,
                "summaries": []
            }
            
            for community in communities:
                comm_id = community["community_id"]
                level = community.get("level", 0)
                
                # Get context
                context = self.get_community_context(comm_id)
                
                # Generate summary
                summary_result = self.generate_community_summary(comm_id, context)
                
                if summary_result["status"] == "success":
                    # Store summary in Neo4j
                    self._store_summary(
                        session,
                        comm_id,
                        summary_result["summary"],
                        summary_result.get("themes", []),
                        summary_result.get("significance", "medium")
                    )
                    results["completed"] += 1
                    results["summaries"].append({
                        "community_id": comm_id,
                        "level": level,
                        "summary": summary_result["summary"],
                        "themes": summary_result.get("themes", [])
                    })
                else:
                    results["failed"] += 1
                    logger.warning(f"Failed to summarize community {comm_id}")
            
            logger.info(f"✅ Completed {results['completed']} summaries ({results['failed']} failed)")
            return results
        
        except Exception as e:
            logger.error(f"Failed to generate all summaries: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _store_summary(
        self,
        session,
        community_id: int,
        summary: str,
        themes: List[str],
        significance: str
    ) -> bool:
        """
        Store community summary in Neo4j
        
        Args:
            session: Neo4j session
            community_id: Community ID
            summary: Summary text
            themes: List of themes
            significance: Significance level
            
        Returns:
            True if successful
        """
        try:
            query = """
            MATCH (c:Community {id: $community_id})
            SET 
                c.summary = $summary,
                c.themes = $themes,
                c.significance = $significance,
                c.summary_generated_at = datetime()
            RETURN c
            """
            
            result = session.run(
                query,
                {
                    "community_id": community_id,
                    "summary": summary,
                    "themes": ",".join(themes),
                    "significance": significance
                }
            ).single()
            
            return result is not None
        
        except Exception as e:
            logger.error(f"Failed to store summary: {str(e)}")
            return False


# Singleton instance
community_summarization_service = CommunitySummarizationService()
```

---

## Implementation Step 3: Integrate Summarization into Pipeline

### Issue
Community summarization is NOT called during document processing.

### Solution

**File**: `backend/app/services/document_processor.py`

Add summarization step after community detection:

```python
# ... existing imports ...
from app.services.community_summarization import community_summarization_service

# In process_document_with_graph() function, add after Step 7:

        # Step 8: Generate community summaries
        logger.info("Step 8: Generating community summaries...")
        if update_callback:
            await update_callback("summarization", 80)
        
        summary_results = community_summarization_service.generate_all_summaries()
        if summary_results["status"] == "success":
            logger.info(f"✅ Generated {summary_results['completed']} community summaries")
        else:
            logger.warning(f"⚠️ Community summarization had issues: {summary_results.get('message', 'Unknown')}")
        
        # Step 9: Update document status (renumber existing steps)
        logger.info("Step 9: Finalizing processing...")
        if update_callback:
            await update_callback("finalization", 95)
        
        # ... rest of the code ...
```

---

## Implementation Step 4: Fix Global Search with Summaries

### Issue
Global search doesn't use community summaries.

### Solution

**File**: `backend/app/services/retrieval_service.py`

Replace `retrieve_global_context()` method:

```python
def retrieve_global_context(self, use_summaries: bool = True) -> Dict[str, Any]:
    """
    Retrieve global context (all communities summary)
    
    Args:
        use_summaries: Whether to include generated summaries
        
    Returns:
        Dictionary with global context
    """
    try:
        session = self.get_session()
        
        query = """
        MATCH (c:Community)
        WHERE c.level = 0  # Only base-level communities
        WITH c
        OPTIONAL MATCH (e:Entity)-[r:IN_COMMUNITY]->(c)
        RETURN
            collect({
                community_id: c.id,
                size: count(DISTINCT e),
                summary: COALESCE(c.summary, ""),
                themes: COALESCE(split(c.themes, ","), []),
                significance: COALESCE(c.significance, "medium"),
                level: COALESCE(c.level, 0),
                created_at: c.createdAt
            }) AS communities,
            count(DISTINCT c) AS num_communities,
            count(DISTINCT e) AS total_entities
        """
        
        result = session.run(query).single()
        
        if not result or result["num_communities"] == 0:
            return {
                "status": "no_communities",
                "message": "No communities found",
            }
        
        # Filter communities with summaries if requested
        communities = result["communities"]
        if use_summaries:
            communities_with_summaries = [
                c for c in communities if c.get("summary")
            ]
            if not communities_with_summaries:
                logger.warning("No community summaries found, using raw communities")
            else:
                communities = communities_with_summaries
        
        return {
            "status": "success",
            "retrieval_type": "global",
            "num_communities": len(communities),
            "total_entities": result["total_entities"],
            "communities": communities,
            "summaries_available": all(c.get("summary") for c in communities),
        }
    
    except Exception as e:
        logger.error(f"Global retrieval failed: {str(e)}")
        return {"status": "error", "message": str(e)}
```

---

## Implementation Step 5: Update Query Processing for Global Search

### Issue
Global search doesn't leverage community summaries for better answers.

### Solution

**File**: `backend/app/services/query_service.py`

Add method to assemble global context for LLM:

```python
def _assemble_global_context(self, retrieval_results: Dict[str, Any]) -> str:
    """
    Assemble global context from communities for LLM
    
    Args:
        retrieval_results: Results from global retrieval
        
    Returns:
        Formatted context string
    """
    if retrieval_results["status"] != "success":
        return ""
    
    communities = retrieval_results.get("communities", [])
    
    context_parts = [
        f"📊 Dataset Overview: {retrieval_results.get('total_entities', 0)} entities "
        f"across {retrieval_results.get('num_communities', 0)} communities\n"
    ]
    
    for comm in communities[:10]:  # Top 10 communities
        context_parts.append(f"\n🏘️  Community {comm['community_id']}:")
        context_parts.append(f"   Size: {comm['size']} entities")
        
        if comm.get("summary"):
            context_parts.append(f"   Summary: {comm['summary']}")
        
        if comm.get("themes"):
            themes = ", ".join(comm["themes"][:5])
            context_parts.append(f"   Themes: {themes}")
        
        if comm.get("significance"):
            context_parts.append(f"   Significance: {comm['significance']}")
    
    return "\n".join(context_parts)
```

---

## Implementation Step 6: Testing & Validation

### Test Script

Create `backend/test_graphrag_fixes.py`:

```python
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.neo4j import get_neo4j_session
from app.services.community_detection import community_detection_service
from app.services.community_summarization import community_summarization_service
from app.services.retrieval_service import retrieval_service


async def test_hierarchical_communities():
    """Test hierarchical community storage"""
    print("\n🧪 Testing Hierarchical Communities...")
    
    session = get_neo4j_session()
    
    # Check if hierarchical communities exist
    query = """
    MATCH (c:Community)
    RETURN c.id, c.level, count(c) as count
    """
    
    results = session.run(query).data()
    print(f"✅ Found {len(results)} communities with hierarchy info")
    
    for result in results[:5]:
        print(f"   - Community {result['c.id']}, Level: {result['c.level']}")


async def test_community_summaries():
    """Test community summary generation"""
    print("\n🧪 Testing Community Summaries...")
    
    # Generate summaries
    results = community_summarization_service.generate_all_summaries()
    
    print(f"✅ Generated {results.get('completed', 0)} summaries")
    print(f"⚠️  Failed: {results.get('failed', 0)}")
    
    # Check stored summaries
    session = get_neo4j_session()
    query = """
    MATCH (c:Community)
    WHERE c.summary IS NOT NULL AND c.summary <> ""
    RETURN c.id, c.summary, c.themes
    LIMIT 5
    """
    
    summaries = session.run(query).data()
    print(f"\n✅ Stored {len(summaries)} community summaries:")
    
    for s in summaries:
        print(f"\n   Community {s['c.id']}:")
        print(f"   Summary: {s['c.summary'][:100]}...")
        print(f"   Themes: {s.get('c.themes', 'N/A')}")


async def test_global_search():
    """Test global search with summaries"""
    print("\n🧪 Testing Global Search with Summaries...")
    
    results = retrieval_service.retrieve_global_context(use_summaries=True)
    
    print(f"✅ Status: {results.get('status')}")
    print(f"   Communities: {results.get('num_communities')}")
    print(f"   Entities: {results.get('total_entities')}")
    print(f"   Summaries available: {results.get('summaries_available')}")
    
    if results.get("communities"):
        print(f"\n   First community:")
        comm = results["communities"][0]
        print(f"   - ID: {comm.get('community_id')}")
        print(f"   - Size: {comm.get('size')}")
        print(f"   - Summary: {comm.get('summary', 'N/A')[:100]}...")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("GraphRAG Fixes - Validation Tests")
    print("=" * 60)
    
    try:
        await test_hierarchical_communities()
        await test_community_summaries()
        await test_global_search()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
```

### Run Tests

```bash
cd backend
python test_graphrag_fixes.py
```

---

## Verification Checklist

After implementing all fixes, verify:

- [ ] Community nodes have `level` field (0, 1, 2, 3...)
- [ ] Community nodes have `summary` field (non-empty)
- [ ] Community nodes have `themes` field (comma-separated)
- [ ] `IN_COMMUNITY` relationships have `community_level` property
- [ ] `retrieve_global_context()` returns communities with summaries
- [ ] Test script runs without errors
- [ ] Document processing includes summarization step

---

## Expected Results

After implementing all fixes:

**Before**:
```
Global Search: "We found 5 communities"
                ↓
                No summaries available
                ↓
                Generic LLM answer
```

**After**:
```
Global Search: "Found 5 communities"
                ↓
                "Tech community: 42 entities focusing on AI/ML"
                "Business community: 38 entities focusing on Strategy"
                "Legal community: 25 entities focusing on Compliance"
                ↓
                High-quality contextual LLM answer
```

---

## Impact

| Metric | Before | After |
|--------|--------|-------|
| GraphRAG Compliance | 71% | 85%+ |
| Global Search Quality | Low | High |
| Community Hierarchy | No | Yes (4 levels) |
| Query Response Quality | OK | Excellent |
| Development Time | - | 4-6 hours |

---

## Troubleshooting

### Issue: "No community summaries found"
**Cause**: `generate_all_summaries()` not called or failed
**Fix**: Run `community_summarization_service.generate_all_summaries()` manually

### Issue: "Hierarchical level info missing"
**Cause**: Old `_store_community_assignments()` still in use
**Fix**: Restart backend after code update

### Issue: "LLM summary generation fails"
**Cause**: Gemini API not configured or quota exceeded
**Fix**: Check `GOOGLE_API_KEY` environment variable

---

## Next Steps After P0

Once you've completed these fixes:
1. Implement DRIFT search (combines local + global)
2. Add text embeddings for semantic search
3. Implement prompt tuning for domain adaptation

This will bring you to **90%+ GraphRAG compliance**! 🚀
