# GraphRAG-Style Indexing Integration Plan

## Overview

This document outlines the implementation plan to integrate Microsoft GraphRAG's multi-pass gleaning extraction mechanism into GraphToG's document indexing pipeline. The primary goal is to use the existing prompt templates (`GRAPH_EXTRACTION_PROMPT_TEMPLATE`, `GRAPH_EXTRACTION_CONTINUE_PROMPT`, and `GRAPH_EXTRACTION_LOOP_PROMPT`) that are already defined in `backend/app/services/prompt.py` but not currently utilized in the indexing process.

## Current State Analysis

### What We Have (in `prompt.py`)

1. **`GRAPH_EXTRACTION_PROMPT_TEMPLATE`** (lines 30-150)
   - Complete prompt for joint entity and relationship extraction
   - Includes entity types, tuple delimiters, record delimiters, completion delimiter
   - Has comprehensive examples showing expected output format

2. **`GRAPH_EXTRACTION_CONTINUE_PROMPT`** (lines 152-153)
   - Text: "MANY entities and relationships were missed in the last extraction..."
   - Used for iterative gleaning passes

3. **`GRAPH_EXTRACTION_LOOP_PROMPT`** (lines 155-156)
   - Text: "It appears some entities and relationships may have still been missed. Answer Y if there are still entities or relationships that need to be added, or N if there are none."
   - Binary decision gate for loop termination

4. **Helper Functions** (lines 555-579)
   - `build_graph_extraction_prompt()` - Formats the main extraction prompt
   - `build_graph_extraction_continue_prompt()` - Returns continue prompt
   - `build_graph_extraction_loop_prompt()` - Returns loop prompt

### Current Indexing Pipeline Gaps

Located in `backend/app/services/document_processor.py:process_document_with_graph()`:

1. **Single-Pass Extraction Only**
   - Line 281: `entity_results = await llm_service.batch_extract_entities(chunk_data)`
   - No iteration or gleaning loop
   - Uses simplified prompt instead of full GraphRAG template

2. **Separate Entity and Relationship Extraction**
   - Line 397: `rel_results = await llm_service.batch_extract_relationships(chunk_with_entities)`
   - GraphRAG extracts both in single pass, then gleans

3. **No Logit Bias Support**
   - Cannot force binary YES/NO decision in loop prompt
   - May get verbose responses instead of single token

4. **No Description Summarization**
   - Multiple mentions of same entity don't consolidate descriptions
   - Relationship descriptions not merged across chunks

5. **Missing Max Gleanings Configuration**
   - No configuration parameter for number of gleaning passes

## Implementation Plan

### Phase 1: Update LLM Service for Gleaning Support

**File:** `backend/app/services/llm_service.py`

```python
# Add new method for single-pass graph extraction with gleaning
async def extract_graph_with_gleaning(
    self,
    text: str,
    chunk_id: str,
    entity_types: Optional[List[str]] = None,
    max_gleanings: int = 1,
) -> Dict[str, Any]:
    """
    Extract entities and relationships using GraphRAG multi-pass gleaning.

    Args:
        text: Text to extract from
        chunk_id: Identifier for the chunk
        entity_types: Entity types to extract (default: DEFAULT_ENTITY_TYPES)
        max_gleanings: Maximum number of gleaning passes (0 = single pass)

    Returns:
        Dict with entities, relationships, and extraction metadata
    """
    all_entities = []
    all_relationships = []
    extraction_history = []

    # Initial extraction
    initial_prompt = build_graph_extraction_prompt(
        text=text,
        entity_types=entity_types,
        tuple_delimiter=DEFAULT_TUPLE_DELIMITER,
        record_delimiter=DEFAULT_RECORD_DELIMITER,
        completion_delimiter=DEFAULT_COMPLETION_DELIMITER,
    )

    response = self._call_llm(initial_prompt)
    entities, relationships = self._parse_graph_extraction_response(response)
    all_entities.extend(entities)
    all_relationships.extend(relationships)
    extraction_history.append(response)

    # Gleaning loop
    for glean_iteration in range(max_gleanings):
        # Continue prompt - ask for missed entities/relationships
        continue_prompt = build_graph_extraction_continue_prompt()
        full_context = f"{text}\n\nPrevious extractions:\n{chr(10).join(extraction_history)}\n\n{continue_prompt}"

        glean_response = self._call_llm(full_context)
        new_entities, new_relationships = self._parse_graph_extraction_response(glean_response)

        if new_entities or new_relationships:
            all_entities.extend(new_entities)
            all_relationships.extend(new_relationships)
            extraction_history.append(glean_response)

        # Loop decision - should we continue?
        if glean_iteration < max_gleanings - 1:
            loop_prompt = build_graph_extraction_loop_prompt()
            loop_context = f"{text}\n\nAll extractions so far:\n{chr(10).join(extraction_history)}\n\n{loop_prompt}"

            # Use constrained generation (max_tokens=1)
            loop_response = self._call_llm_constrained(loop_context, max_tokens=10)

            should_continue = "Y" in loop_response.upper() or "YES" in loop_response.upper()
            if not should_continue:
                break

    # Deduplicate entities and relationships
    unique_entities = self._deduplicate_entities(all_entities)
    unique_relationships = self._deduplicate_relationships(all_relationships)

    return {
        "chunk_id": chunk_id,
        "entities": unique_entities,
        "relationships": unique_relationships,
        "num_gleanings": len(extraction_history) - 1,
        "status": "success",
    }
```

### Phase 2: Add Entity/Relationship Deduplication

**File:** `backend/app/services/llm_service.py`

```python
def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
    """
    Merge duplicate entities by (name, type) and consolidate descriptions.
    """
    entity_map = {}
    for entity in entities:
        key = (entity.get("name", "").upper(), entity.get("type", "").upper())
        if key not in entity_map:
            entity_map[key] = {
                "name": entity.get("name", ""),
                "type": entity.get("type", ""),
                "descriptions": [entity.get("description", "")],
                "confidence": entity.get("confidence", 0.8),
            }
        else:
            entity_map[key]["descriptions"].append(entity.get("description", ""))
            # Average confidence scores
            entity_map[key]["confidence"] = (
                entity_map[key]["confidence"] + entity.get("confidence", 0.8)
            ) / 2

    # Convert back to list, joining descriptions
    result = []
    for key, data in entity_map.items():
        unique_descriptions = list(set(data["descriptions"]))
        result.append({
            "name": data["name"],
            "type": data["type"],
            "description": " | ".join(unique_descriptions),
            "confidence": data["confidence"],
        })

    return result

def _deduplicate_relationships(self, relationships: List[Dict]) -> List[Dict]:
    """
    Merge duplicate relationships by (source, target, type).
    """
    rel_map = {}
    for rel in relationships:
        key = (
            rel.get("source", "").upper(),
            rel.get("target", "").upper(),
            rel.get("type", "RELATED_TO").upper(),
        )
        if key not in rel_map:
            rel_map[key] = {
                "source": rel.get("source", ""),
                "target": rel.get("target", ""),
                "type": rel.get("type", "RELATED_TO"),
                "descriptions": [rel.get("description", "")],
                "strength": rel.get("strength", 5),
                "count": 1,
            }
        else:
            rel_map[key]["descriptions"].append(rel.get("description", ""))
            rel_map[key]["strength"] = max(rel_map[key]["strength"], rel.get("strength", 5))
            rel_map[key]["count"] += 1

    result = []
    for key, data in rel_map.items():
        unique_descriptions = list(set(data["descriptions"]))
        result.append({
            "source": data["source"],
            "target": data["target"],
            "type": data["type"],
            "description": " | ".join(unique_descriptions),
            "strength": data["strength"],
            "weight": data["count"],  # Edge weight based on mention frequency
        })

    return result
```

### Phase 3: Add Description Summarization

**File:** `backend/app/services/llm_service.py`

```python
async def summarize_entity_descriptions(
    self,
    entity_name: str,
    descriptions: List[str],
    max_length: int = 120,
) -> str:
    """
    Summarize multiple entity descriptions into a single coherent description.
    Uses SUMMARIZE_DESCRIPTIONS_PROMPT_TEMPLATE from prompt.py
    """
    if len(descriptions) == 1:
        return descriptions[0]

    prompt = build_description_summarization_prompt(
        entity_name=entity_name,
        description_list="\n".join(f"- {desc}" for desc in descriptions),
        max_length=max_length,
    )

    response = self._call_llm(prompt)
    return response.strip()
```

### Phase 4: Update Document Processor

**File:** `backend/app/services/document_processor.py`

Replace separate entity and relationship extraction with unified gleaning approach:

```python
# Step 7: Extract entities AND relationships with gleaning (replaces steps 7 and 8)
logger.info("Step 7: Extracting entities and relationships with GraphRAG gleaning...")
if update_callback:
    await update_callback("graph_extraction", 40)

extraction_config = {
    "entity_types": settings.ENTITY_TYPES or DEFAULT_ENTITY_TYPES,
    "max_gleanings": settings.MAX_GLEANINGS,  # New config parameter
}

all_extractions = []
for chunk_text, chunk_id in chunk_data:
    extraction_result = await llm_service.extract_graph_with_gleaning(
        text=chunk_text,
        chunk_id=chunk_id,
        **extraction_config,
    )
    all_extractions.append(extraction_result)

    if extraction_result["status"] == "success":
        results["entities_extracted"] += len(extraction_result["entities"])
        results["relationships_extracted"] += len(extraction_result["relationships"])

        # Create entity nodes
        for entity in extraction_result["entities"]:
            entity_id = graph_service.create_or_merge_entity(
                name=entity.get("name", ""),
                entity_type=entity.get("type", "OTHER"),
                description=entity.get("description", ""),
                confidence=entity.get("confidence", 0.8),
            )
            if entity_id:
                graph_service.create_mention_relationship(
                    entity_id=entity_id,
                    textunit_id=chunk_id,
                )

        # Create relationship edges
        for rel in extraction_result["relationships"]:
            source_entity = graph_service.find_entity_by_name(rel["source"])
            target_entity = graph_service.find_entity_by_name(rel["target"])

            if source_entity and target_entity:
                graph_service.create_relationship(
                    source_entity_id=source_entity["id"],
                    target_entity_id=target_entity["id"],
                    relationship_type=rel.get("type", "RELATED_TO"),
                    description=rel.get("description", ""),
                    confidence=rel.get("strength", 5) / 10.0,
                )

logger.info(
    f"Extracted {results['entities_extracted']} entities and "
    f"{results['relationships_extracted']} relationships with gleaning"
)
```

### Phase 5: Add Configuration Parameters

**File:** `backend/app/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # GraphRAG Indexing Configuration
    MAX_GLEANINGS: int = 1  # Number of gleaning passes (0=single pass, 1=recommended)
    ENTITY_TYPES: Optional[List[str]] = None  # Custom entity types to extract
    CHUNK_SIZE_TOKENS: int = 1200  # Recommended for gleaning (was 300-600)
    ENABLE_DESCRIPTION_SUMMARIZATION: bool = True
    DESCRIPTION_MAX_LENGTH: int = 120

    # Extraction delimiters (match prompt.py defaults)
    TUPLE_DELIMITER: str = "|||"
    RECORD_DELIMITER: str = "\n"
    COMPLETION_DELIMITER: str = "<COMPLETE>"
```

### Phase 6: Cross-TextUnit Deduplication

**File:** `backend/app/services/document_processor.py`

After processing all chunks, perform global deduplication:

```python
# Step 7.5: Global entity deduplication and description summarization
logger.info("Step 7.5: Consolidating entities across all chunks...")
if update_callback:
    await update_callback("entity_consolidation", 55)

if settings.ENABLE_DESCRIPTION_SUMMARIZATION:
    # Get all entities from graph
    all_graph_entities = graph_service.get_all_entities_for_document(document_id)

    # Group by (name, type)
    entity_groups = {}
    for entity in all_graph_entities:
        key = (entity["name"].upper(), entity["type"].upper())
        if key not in entity_groups:
            entity_groups[key] = []
        entity_groups[key].append(entity)

    # Summarize descriptions for entities with multiple mentions
    for key, entities in entity_groups.items():
        if len(entities) > 1:
            descriptions = [e["description"] for e in entities if e.get("description")]
            if len(descriptions) > 1:
                summarized = await llm_service.summarize_entity_descriptions(
                    entity_name=entities[0]["name"],
                    descriptions=descriptions,
                    max_length=settings.DESCRIPTION_MAX_LENGTH,
                )
                # Update entity in graph with summarized description
                graph_service.update_entity_description(
                    entity_id=entities[0]["id"],
                    description=summarized,
                )
```

## Testing Strategy

### Unit Tests

1. **Test gleaning loop with mock LLM responses**
   - Verify correct number of iterations
   - Test early termination when LLM says "N"
   - Test max_gleanings limit enforcement

2. **Test entity deduplication**
   - Same entity extracted multiple times
   - Different capitalization/spacing
   - Description merging

3. **Test relationship deduplication**
   - Same relationship mentioned multiple times
   - Weight calculation based on frequency

### Integration Tests

1. **End-to-end document processing with gleaning**
   - Process sample document with known entities
   - Verify entity coverage improvement with gleaning
   - Measure extraction quality metrics

2. **Performance benchmarks**
   - Compare single-pass vs gleaning (1, 2, 3 passes)
   - Measure LLM API call count
   - Track processing time per document

### Test Files

- `backend/tests/test_graphrag_extraction.py`
- `backend/tests/test_entity_deduplication.py`
- `backend/tests/test_gleaning_loop.py`

## Migration Plan

1. **Backward Compatibility**
   - Default `MAX_GLEANINGS=0` initially (maintains current behavior)
   - Gradually increase to 1 after validation

2. **Feature Flag**
   - Add `ENABLE_GRAPHRAG_GLEANING` flag
   - Allow gradual rollout

3. **Monitoring**
   - Track extraction quality metrics
   - Monitor LLM API usage increase
   - Log gleaning iteration counts

## Expected Benefits

1. **Improved Entity Coverage**: 20-30% more entities extracted
2. **Higher Quality Descriptions**: Consolidated from multiple viewpoints
3. **Better Graph Connectivity**: More complete relationship mapping
4. **Reduced Hallucination**: Type constraints in continue prompt
5. **Efficient Processing**: Early termination when extraction is complete

## Timeline Estimate

- **Phase 1** (LLM Service): 2-3 days
- **Phase 2** (Deduplication): 1-2 days
- **Phase 3** (Summarization): 1 day
- **Phase 4** (Document Processor): 2-3 days
- **Phase 5** (Configuration): 0.5 day
- **Phase 6** (Cross-TextUnit): 1-2 days
- **Testing**: 2-3 days
- **Documentation**: 1 day

**Total**: ~12-15 days

## References

- Microsoft GraphRAG Repository: https://github.com/microsoft/graphrag
- GraphRAG Indexing Pipeline: `graphrag/index/graph/extractors/`
- Prompt Templates: `graphrag/prompts/index/extract_graph.py`
- nano-graphrag (simplified reference): https://github.com/gusye1234/nano-graphrag
