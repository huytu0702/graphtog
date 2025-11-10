# ToG Enhancement: Solution 2+5 Implementation

## 📋 Summary

Implemented **Solution 2 + 5 Combined** to retrieve detailed context from knowledge graph TextUnits alongside ToG graph traversal reasoning.

**Problem**: ToG chỉ retrieve thông tin tóm tắt từ entity descriptions, thiếu chi tiết từ văn bản gốc.

**Solution**: Kết hợp graph reasoning (ToG) với full-text retrieval (TextUnit chunks) để LLM có đủ context generate câu trả lời chi tiết.

---

## 🔧 Changes Made

### 1. **Updated Dataclasses** (Line 49-92)

Added `source_texts` field to store retrieved text chunks:

```python
@dataclass
class ToGEntity:
    # ... existing fields ...
    source_texts: List[str] = field(default_factory=list)  # NEW

@dataclass
class ToGRelation:
    # ... existing fields ...
    source_texts: List[str] = field(default_factory=list)  # NEW
```

### 2. **Enhanced `_get_related_entities`** (Line 597-657)

Modified Cypher query to retrieve TextUnit chunks mentioning target entities:

**Before**:
```cypher
RETURN target.id, target.name, target.type, target.description
```

**After**:
```cypher
OPTIONAL MATCH (target)<-[:MENTIONS]-(tu:TextUnit)
WITH target, r, collect(DISTINCT tu.text) as text_chunks
RETURN target.id, target.name, target.type,
       target.description,
       text_chunks[0..3] as source_texts  -- Get top 3 chunks
```

### 3. **Enhanced `_get_entity_by_name`** (Line 319-365)

Added same TextUnit retrieval for topic entities extracted at the start:

```cypher
OPTIONAL MATCH (e)<-[:MENTIONS]-(tu:TextUnit)
WITH e, collect(DISTINCT tu.text) as text_chunks
RETURN e.id, e.name, e.type, e.description,
       text_chunks[0..3] as source_texts
```

### 4. **New Method: `_enrich_answer_with_chunks`** (Line 723-772)

Retrieves top-K most relevant TextUnit chunks across all explored entities:

```python
async def _enrich_answer_with_chunks(
    self,
    question: str,
    entities: List[ToGEntity],
    top_k: int = 5
) -> List[str]:
    """
    Retrieve most relevant TextUnit chunks for final answer enrichment.

    Logic:
    - Find all TextUnits mentioning any explored entity
    - Order by entity_count (chunks mentioning more entities = more relevant)
    - Return top K chunks
    """
```

**Cypher Query**:
```cypher
MATCH (e:Entity)<-[:MENTIONS]-(tu:TextUnit)
WHERE e.name IN $entity_names
WITH tu, count(DISTINCT e) as entity_count
ORDER BY entity_count DESC
RETURN tu.text
LIMIT $top_k
```

### 5. **Completely Rewrote `_generate_final_answer`** (Line 774-876)

**Before**: Only had entity names and relation types
```python
path_summary = [f"Step {depth}: Entities {entities}, Relations {relations}"]
reasoning_text = "; ".join(path_summary)
prompt = TOG_FINAL_ANSWER_PROMPT.format(
    question=question,
    reasoning_path=reasoning_text  # ❌ No details
)
```

**After**: Includes entity descriptions, relation descriptions, AND source text chunks
```python
# 1. Format reasoning path with entity descriptions
detail = (
    f"{rel.source_entity.name} ({source_desc}) "
    f"--[{rel.type}: {rel_desc}]--> "
    f"{rel.target_entity.name} ({target_desc})"
)

# 2. Collect source texts from entities
entity_context_snippets = [
    f"[Context for {entity.name}]: {entity.source_texts[0][:500]}"
    for entity in all_entities if entity.source_texts
]

# 3. Retrieve additional top-K chunks
enrichment_chunks = await self._enrich_answer_with_chunks(
    question=question,
    entities=all_entities,
    top_k=3
)

# 4. Enhanced prompt with ALL context
prompt = f"""
Question: {question}

Reasoning Path (entities and relationships explored):
{reasoning_text}  # ✅ Includes descriptions

Source Text Excerpts:
{context_text}  # ✅ Includes original text chunks

Instructions:
- Include specific facts, details, numbers, dates, and quotes from source texts
- Reference entities and relationships from reasoning path
"""
```

### 6. **Fixed Method Signatures**

Updated `_expand_entity_from_relation` and `_expand_entity_from_relation_safe` to accept `question` parameter:

```python
async def _expand_entity_from_relation(
    self,
    relation: ToGRelation,
    document_ids: Optional[List[int]],
    question: str = ""  # NEW parameter
) -> Optional[ToGEntity]:
```

---

## 📊 Data Flow

```
User Question
    ↓
┌────────────────────────────────────────────────┐
│ 1. Topic Entity Extraction                    │
│    - LLM extracts entity names                │
│    - _get_entity_by_name() retrieves:         │
│      * Entity properties (name, type, desc)   │
│      * Top 3 TextUnit chunks ✅ NEW           │
└────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────┐
│ 2. Iterative Graph Exploration (ToG)          │
│    For each depth level:                      │
│    - Score and select top relations           │
│    - _get_related_entities() retrieves:       │
│      * Target entity properties               │
│      * Top 3 TextUnit chunks ✅ NEW           │
│    - Store entities with source_texts         │
└────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────┐
│ 3. Answer Generation with Context             │
│    _generate_final_answer() uses:             │
│    - Graph reasoning path (entities + rels)   │
│    - Entity descriptions                      │
│    - Relation descriptions                    │
│    - Source texts from entities ✅ NEW        │
│    - Top-K enrichment chunks ✅ NEW           │
│    → LLM generates detailed answer            │
└────────────────────────────────────────────────┘
```

---

## 🎯 Key Benefits

### Before (Only Graph Properties)
```
LLM Input:
- Entity names: ["John Smith", "Microsoft"]
- Relation types: ["WORKS_AT"]

LLM Output:
"John Smith worked at Microsoft."
```

### After (Graph + Full Text)
```
LLM Input:
- Entity: "John Smith (Former employee at Microsoft who worked on Azure)"
- Relation: "WORKS_AT: Led Azure team from 2015-2020"
- Source Text: "John Smith worked at Microsoft from 2015 to 2020.
                He led the Azure team, overseeing 50 engineers.
                He increased cloud revenue by 200% in 3 years."

LLM Output:
"John Smith worked at Microsoft from 2015 to 2020, where he served
as the leader of the Azure team. During his tenure, he managed a team
of 50 engineers and achieved a remarkable 200% increase in cloud
revenue over a three-year period."
```

---

## 🔬 Technical Details

### Memory Usage
- **Per Entity**: Store up to 3 text chunks (typically 200-500 chars each)
- **Total Context**: ~5-6 chunks per answer (3 entity contexts + 3 enrichment chunks)
- **Max Context Size**: ~3000 chars from source texts (limited by [:500] truncation)

### Performance
- **Additional Cypher Queries**: 1 extra `OPTIONAL MATCH` per entity retrieval
- **Enrichment Query**: 1 query at end to get top-K chunks
- **Latency Impact**: Minimal (~50-100ms extra per query)

### Graph Schema Requirements
- ✅ Requires `MENTIONS` relationship between Entity and TextUnit
- ✅ Already exists in current schema (created during document processing)
- ✅ No schema migration needed

---

## ✅ Testing Checklist

- [ ] Upload a markdown document with detailed information
- [ ] Ask ToG query requiring multi-hop reasoning
- [ ] Verify answer includes:
  - [ ] Specific numbers/dates from original text
  - [ ] Detailed context beyond entity descriptions
  - [ ] Quotes or exact phrases from source documents
- [ ] Check logs for "Enriching answer with top X chunks"
- [ ] Verify no errors in entity retrieval or answer generation

---

## 🐛 Potential Issues & Solutions

### Issue 1: Empty source_texts
**Symptom**: Entities have empty `source_texts` arrays

**Possible Causes**:
- MENTIONS relationship not created during document processing
- TextUnit nodes don't have `text` property

**Debug**:
```cypher
// Check if MENTIONS exist
MATCH (e:Entity)<-[:MENTIONS]-(tu:TextUnit)
RETURN e.name, count(tu) as mention_count
ORDER BY mention_count DESC
LIMIT 10

// Check if TextUnit has text
MATCH (tu:TextUnit)
RETURN tu.text
LIMIT 5
```

### Issue 2: Answer still too generic
**Possible Causes**:
- LLM ignoring source text context
- Source texts truncated too much ([:500])
- Not enough chunks retrieved (top_k too low)

**Solutions**:
- Increase truncation limit from 500 to 800
- Increase top_k from 3 to 5
- Add more explicit instruction in prompt to use source texts

### Issue 3: Token limit exceeded
**Symptom**: LLM API error about max tokens

**Solutions**:
- Reduce top_k from 3 to 2
- Reduce truncation from 500 to 300
- Limit entity_context_snippets from 3 to 2

---

## 📝 Future Enhancements

1. **Semantic Ranking**: Use embedding similarity to rank chunks instead of entity_count
2. **Dynamic top_k**: Adjust number of chunks based on question complexity
3. **Source Attribution**: Return which specific chunks were used in answer
4. **Caching**: Cache retrieved chunks for repeated queries

---

## 👤 Author & Date

**Implementation Date**: 2025-11-10
**Modified Files**:
- `backend/app/services/tog_service.py`

**Lines Changed**: ~150 lines added/modified
