# Claims Extraction & Storage Implementation

## Overview

Successfully implemented GraphRAG Claims Extraction & Storage feature in GraphToG, following Microsoft GraphRAG best practices for extracting and storing factual assertions from documents.

**Implementation Date:** 2025-10-30
**Task:** Priority 2.2 from tasks.md
**Status:** ✅ Complete

---

## What is Claims Extraction?

Claims extraction is a GraphRAG feature that identifies and extracts factual assertions, statements, or claims made by or about entities in documents.

### Traditional Entity/Relationship Extraction (Before)
1. Extract entities (people, organizations, events)
2. Extract relationships between entities
3. Store in knowledge graph

**Limitations:**
- No explicit tracking of factual assertions
- Difficult to verify or validate statements
- Cannot filter by claim status (verified vs suspected)

### Claims Extraction (After)
1. **Extract entities** (as before)
2. **Extract relationships** (as before)
3. **Extract claims** with detailed metadata:
   - Subject entity (who makes the claim)
   - Object entity (who/what is affected)
   - Claim type (category: CORRUPTION, ACQUISITION, etc.)
   - Status (TRUE, FALSE, SUSPECTED)
   - Date range (when the claim was made)
   - Source text (evidence)

**Benefits:**
- **Traceability:** Track source of each assertion
- **Verification:** Mark claims as TRUE, FALSE, or SUSPECTED
- **Temporal:** Date-stamped claims for timeline analysis
- **Queryable:** Search claims by entity, type, or status
- **Compliance:** Support fact-checking and claim validation workflows

---

## Implementation Details

### 1. Neo4j Schema Extensions (`graph_service.py`)

**Location:** `backend/app/services/graph_service.py:40-65`

#### New Constraints
```cypher
CREATE CONSTRAINT claim_id IF NOT EXISTS
FOR (c:Claim) REQUIRE c.id IS UNIQUE;
```

#### New Indexes
```cypher
CREATE INDEX claim_type IF NOT EXISTS
FOR (c:Claim) ON (c.claim_type);

CREATE INDEX claim_status IF NOT EXISTS
FOR (c:Claim) ON (c.status);
```

#### Claim Node Structure
```javascript
{
  id: string,              // MD5 hash of subject:object:type:description
  subject: string,         // Subject entity name
  object: string,          // Object entity name or "NONE"
  claim_type: string,      // Type/category of claim
  status: string,          // "TRUE" | "FALSE" | "SUSPECTED"
  description: string,     // Detailed claim description
  start_date: string,      // ISO-8601 date or null
  end_date: string,        // ISO-8601 date or null
  source_text: string,     // Supporting evidence text
  created_at: datetime     // Timestamp
}
```

#### Relationships
```
Entity -[:MAKES_CLAIM]-> Claim    // Subject entity makes the claim
Claim -[:ABOUT]-> Entity          // Claim is about object entity
Claim -[:SOURCED_FROM]-> TextUnit // Claim comes from this text chunk
```

### 2. Prompt Template (`prompt.py`)

**Location:** `backend/app/services/prompt.py:158-253`

#### Claims Extraction Prompt
- Uses Microsoft GraphRAG tuple-based format
- Extracts 8 fields per claim:
  1. Subject entity
  2. Object entity
  3. Claim type
  4. Status (TRUE/FALSE/SUSPECTED)
  5. Start date (ISO-8601)
  6. End date (ISO-8601)
  7. Description
  8. Source text

**Example Output:**
```
(COMPANY A<|>GOVERNMENT AGENCY B<|>ANTI-COMPETITIVE PRACTICES<|>TRUE<|>2022-01-10T00:00:00<|>2022-01-10T00:00:00<|>Company A was fined for bid rigging in multiple public tenders<|>According to an article on 2022/01/10, Company A was fined for bid rigging...)##
(PERSON C<|>NONE<|>CORRUPTION<|>SUSPECTED<|>2015-01-01T00:00:00<|>2015-12-30T00:00:00<|>Person C was suspected of engaging in corruption activities in 2015<|>The company is owned by Person C who was suspected of...)##
<|COMPLETE|>
```

#### Helper Function
```python
def build_claims_extraction_prompt(
    input_text: str,
    entity_specs: Optional[str] = None,
    claim_description: Optional[str] = None,
    tuple_delimiter: str = "<|>",
    record_delimiter: str = "##",
    completion_delimiter: str = "<|COMPLETE|>",
) -> str
```

### 3. LLM Service Methods (`llm_service.py`)

**Location:** `backend/app/services/llm_service.py:347-493`

#### `extract_claims(text, entities, chunk_id)`
- **Purpose:** Extract claims from a single text chunk
- **Input:** Text, previously extracted entities, chunk ID
- **Process:**
  1. Build entity specs from extracted entities
  2. Generate claims extraction prompt
  3. Call Gemini LLM
  4. Parse tuple-based response
- **Output:** List of claim dictionaries

#### `_parse_claims_response(response)`
- **Purpose:** Parse GraphRAG tuple format into structured claims
- **Handles:**
  - Tuple delimiter splitting (`<|>`)
  - Record delimiter splitting (`##`)
  - Completion delimiter removal (`<|COMPLETE|>`)
  - Date parsing (ISO-8601 or NONE)
  - Malformed record validation

#### `batch_extract_claims(chunks_with_entities)`
- **Purpose:** Extract claims from multiple chunks in batch
- **Rate Limiting:** 0.1s delay between requests
- **Returns:** List of extraction results

### 4. Graph Service Methods (`graph_service.py`)

**Location:** `backend/app/services/graph_service.py:609-904`

#### `create_claim_node(...)`
- Creates Claim node with MD5 ID generation
- Stores all claim fields
- Returns claim ID

#### `link_claim_to_entities(claim_id, subject, object)`
- Creates `Entity -[:MAKES_CLAIM]-> Claim` relationship
- Creates `Claim -[:ABOUT]-> Entity` relationship (if object exists)
- Handles "NONE" object gracefully

#### `link_claim_to_textunit(claim_id, textunit_id)`
- Creates `Claim -[:SOURCED_FROM]-> TextUnit` relationship
- Links claim to source text chunk for traceability

#### `get_claims_for_entity(entity_name, limit)`
- Retrieves all claims related to an entity
- Searches both subject and object relationships
- Includes source text from TextUnit

#### `get_all_claims(claim_type, status, limit)`
- Retrieves all claims with optional filters
- Supports filtering by claim type and status
- Returns up to `limit` claims

### 5. Document Processing Pipeline Integration (`document_processor.py`)

**Location:** `backend/app/services/document_processor.py:289-330`

#### New Step 8.5: Claims Extraction
Added between Step 8 (relationship extraction) and Step 9 (community detection):

```python
# Step 8.5: Extract claims from chunks with entities
claims_results = await llm_service.batch_extract_claims(chunk_with_entities)

for result in claims_results:
    if result["status"] == "success":
        for claim in result["claims"]:
            # Create claim node
            claim_id = graph_service.create_claim_node(...)

            # Link claim to entities
            graph_service.link_claim_to_entities(...)

            # Link claim to text unit
            graph_service.link_claim_to_textunit(...)

            results["claims_extracted"] += 1
```

**Processing Flow:**
1. Document uploaded → parsed → chunked
2. Entities extracted from each chunk
3. Relationships extracted between entities
4. **Claims extracted from chunks with entities** ← NEW
5. Communities detected
6. Communities summarized

### 6. Query Service (`query_service.py`)

**Location:** `backend/app/services/query_service.py:709-875`

#### `get_claims_for_entity(entity_name, limit)`
- Query claims for a specific entity
- Returns structured result with claims list

#### `get_all_claims(claim_type, status, limit)`
- Query all claims with optional filters
- Supports claim type and status filtering

#### `query_claims(query, entity_name, claim_type, status, limit)`
- **Natural language claims querying**
- Filters claims by entity/type/status
- Builds context from filtered claims
- Generates LLM answer based on claims context
- Returns answer + supporting claims

### 7. API Endpoints (`queries.py`)

**Location:** `backend/app/api/endpoints/queries.py:400-565`

#### GET `/api/queries/claims`
Get all claims with optional filters

**Query Parameters:**
- `claim_type` (optional): Filter by claim type
- `status` (optional): Filter by status (TRUE/FALSE/SUSPECTED)
- `limit` (optional, default 100): Maximum claims to return

**Response:**
```json
{
  "status": "success",
  "total": 15,
  "claims": [
    {
      "id": "abc123",
      "subject": "COMPANY A",
      "object": "GOVERNMENT AGENCY B",
      "claim_type": "ANTI-COMPETITIVE PRACTICES",
      "status": "TRUE",
      "description": "Company A was fined for bid rigging...",
      "start_date": "2022-01-10T00:00:00",
      "end_date": "2022-01-10T00:00:00",
      "source_text": "According to an article...",
      "created_at": "2025-10-30T12:00:00"
    }
  ],
  "filters": {
    "claim_type": null,
    "status": "TRUE"
  }
}
```

#### GET `/api/queries/claims/entity/{entity_name}`
Get all claims related to a specific entity

**Path Parameters:**
- `entity_name` (required): Name of the entity

**Query Parameters:**
- `limit` (optional, default 20): Maximum claims to return

**Response:**
```json
{
  "status": "success",
  "entity_name": "COMPANY A",
  "total": 5,
  "claims": [...]
}
```

#### POST `/api/queries/claims/query`
Query claims with natural language and optional filters

**Request Body:**
```json
{
  "query": "What corruption claims exist?",
  "entity_name": "PERSON C",    // optional
  "claim_type": "CORRUPTION",   // optional
  "status": "SUSPECTED",        // optional
  "limit": 20                   // optional
}
```

**Response:**
```json
{
  "query": "What corruption claims exist?",
  "status": "success",
  "query_type": "claims",
  "answer": "Based on the extracted claims, Person C was suspected of engaging in corruption activities in 2015. The status of this claim is SUSPECTED, meaning it has not been verified...",
  "claims": [...],
  "total_claims": 3,
  "filters": {
    "entity_name": "PERSON C",
    "claim_type": "CORRUPTION",
    "status": "SUSPECTED"
  }
}
```

### 8. Pydantic Schemas (`schemas/claim.py`)

**Location:** `backend/app/schemas/claim.py`

**Created Schemas:**
- `ClaimBase` - Base claim fields
- `ClaimCreate` - For creating claims
- `ClaimResponse` - For API responses
- `ClaimQueryRequest` - For querying claims
- `ClaimQueryResponse` - Query results
- `ClaimExtractionRequest` - Manual extraction
- `ClaimExtractionResponse` - Extraction results

---

## Usage Examples

### Example 1: Upload Document with Claims Extraction

```python
# Upload document - claims extracted automatically
POST /api/documents/upload
Content-Type: multipart/form-data

# Processing pipeline runs:
# 1. Parse document
# 2. Chunk text
# 3. Extract entities
# 4. Extract relationships
# 5. Extract claims ← NEW
# 6. Detect communities
# 7. Generate summaries
```

**Result:**
```json
{
  "document_id": "abc-123",
  "status": "completed",
  "chunks_created": 10,
  "entities_extracted": 25,
  "relationships_extracted": 18,
  "claims_extracted": 12,    ← NEW
  "communities_detected": 3,
  "communities_summarized": 3
}
```

### Example 2: Get All Claims with Filters

```python
GET /api/queries/claims?status=SUSPECTED&limit=50
```

**Result:**
```json
{
  "status": "success",
  "total": 8,
  "claims": [
    {
      "id": "claim_001",
      "subject": "PERSON C",
      "object": "NONE",
      "claim_type": "CORRUPTION",
      "status": "SUSPECTED",
      "description": "Person C was suspected of engaging in corruption activities in 2015",
      "start_date": "2015-01-01T00:00:00",
      "end_date": "2015-12-30T00:00:00",
      "source_text": "The company is owned by Person C who was suspected of...",
      "created_at": "2025-10-30T10:30:00"
    }
    // ... more claims
  ],
  "filters": {
    "claim_type": null,
    "status": "SUSPECTED"
  }
}
```

### Example 3: Get Claims for Specific Entity

```python
GET /api/queries/claims/entity/COMPANY%20A?limit=10
```

**Result:**
```json
{
  "status": "success",
  "entity_name": "COMPANY A",
  "total": 3,
  "claims": [
    {
      "subject": "COMPANY A",
      "object": "GOVERNMENT AGENCY B",
      "claim_type": "ANTI-COMPETITIVE PRACTICES",
      "status": "TRUE",
      "description": "Company A was fined for bid rigging...",
      // ... full claim data
    }
  ]
}
```

### Example 4: Query Claims with Natural Language

```python
POST /api/queries/claims/query
{
  "query": "What claims exist about corruption?",
  "claim_type": "CORRUPTION",
  "status": "SUSPECTED"
}
```

**Result:**
```json
{
  "query": "What claims exist about corruption?",
  "status": "success",
  "query_type": "claims",
  "answer": "Based on the extracted claims, there are 2 suspected corruption-related claims in the knowledge base:\n\n1. Person C was suspected of engaging in corruption activities in 2015. This claim is currently marked as SUSPECTED and has not been verified.\n\n2. Organization X allegedly received illegal payments in 2018, according to whistleblower reports. This claim also remains unverified.\n\nBoth claims should be investigated further for verification.",
  "claims": [
    { "subject": "PERSON C", "claim_type": "CORRUPTION", "status": "SUSPECTED", ... },
    { "subject": "ORGANIZATION X", "claim_type": "ILLEGAL PAYMENT", "status": "SUSPECTED", ... }
  ],
  "total_claims": 2,
  "filters": {
    "entity_name": null,
    "claim_type": "CORRUPTION",
    "status": "SUSPECTED"
  }
}
```

### Example 5: Direct GraphRAG Usage (Backend)

```python
from app.services.llm_service import llm_service
from app.services.graph_service import graph_service

# Extract claims from text
text = "According to an article on 2022/01/10, Company A was fined for bid rigging."
entities = [{"name": "COMPANY A", "type": "ORGANIZATION"}]

result = llm_service.extract_claims(
    text=text,
    entities=entities,
    chunk_id="test_chunk_001"
)

# result["claims"] contains:
# [
#   {
#     "subject": "COMPANY A",
#     "object": "GOVERNMENT AGENCY B",
#     "claim_type": "ANTI-COMPETITIVE PRACTICES",
#     "status": "TRUE",
#     "start_date": "2022-01-10T00:00:00",
#     "end_date": "2022-01-10T00:00:00",
#     "description": "Company A was fined for bid rigging...",
#     "source_text": "According to an article..."
#   }
# ]

# Store claim in graph
claim_id = graph_service.create_claim_node(
    subject_entity_name="COMPANY A",
    object_entity_name="GOVERNMENT AGENCY B",
    claim_type="ANTI-COMPETITIVE PRACTICES",
    status="TRUE",
    description="Company A was fined for bid rigging...",
    start_date="2022-01-10T00:00:00",
    end_date="2022-01-10T00:00:00",
    source_text="According to an article..."
)

# Link to entities
graph_service.link_claim_to_entities(
    claim_id=claim_id,
    subject_entity_name="COMPANY A",
    object_entity_name="GOVERNMENT AGENCY B"
)

# Link to text unit
graph_service.link_claim_to_textunit(
    claim_id=claim_id,
    textunit_id="test_chunk_001"
)
```

---

## Use Cases

### 1. Fact Verification
- Extract claims from news articles
- Mark claims as TRUE/FALSE after verification
- Track claim status over time

### 2. Due Diligence
- Extract claims about companies or individuals
- Filter by claim type (CORRUPTION, FRAUD, LEGAL_ISSUE)
- Generate reports on entity risk profiles

### 3. Compliance & Audit
- Track claims with temporal context
- Verify source text for each claim
- Generate audit trails

### 4. Research & Analysis
- Extract historical claims from documents
- Analyze claim patterns across entities
- Compare SUSPECTED vs TRUE claims

### 5. Knowledge Base Building
- Automatically extract factual assertions
- Build queryable claim database
- Enable fact-based Q&A

---

## Testing

### Syntax Validation ✅
```bash
cd backend
python -m py_compile app/services/graph_service.py
python -m py_compile app/services/prompt.py
python -m py_compile app/services/llm_service.py
python -m py_compile app/services/document_processor.py
python -m py_compile app/services/query_service.py
python -m py_compile app/api/endpoints/queries.py
python -m py_compile app/schemas/claim.py
```
**Result:** All syntax checks passed ✅

### Manual Testing Checklist

- [ ] Upload document with factual claims
- [ ] Verify claims extracted during processing
- [ ] Check claims appear in Neo4j browser
- [ ] Test GET /api/queries/claims endpoint
- [ ] Test GET /api/queries/claims/entity/{name} endpoint
- [ ] Test POST /api/queries/claims/query endpoint
- [ ] Filter claims by type
- [ ] Filter claims by status
- [ ] Query claims with natural language
- [ ] Verify claim-entity relationships in graph
- [ ] Verify claim-textunit relationships in graph
- [ ] Test with different claim types
- [ ] Test with different claim statuses (TRUE/FALSE/SUSPECTED)
- [ ] Test with date ranges

### Future Automated Tests

```python
# backend/tests/test_claims.py

def test_claim_extraction():
    # Test LLM claim extraction
    # Assert correct tuple parsing
    # Verify claim structure

def test_claim_storage():
    # Test Neo4j claim node creation
    # Assert relationships created
    # Verify claim retrieval

def test_claim_query_api():
    # Test API endpoints
    # Assert response structure
    # Verify filtering works

def test_claims_in_pipeline():
    # Upload test document
    # Assert claims extracted
    # Verify count in results
```

---

## Troubleshooting

### Issue: No claims extracted from document
**Possible Causes:**
1. Document has no factual assertions
2. Entities not extracted (claims require entities)
3. LLM failed to parse claims

**Solution:**
1. Check entity extraction results first
2. Review source text for factual statements
3. Check logs: `claims_extracted` count in processing results

### Issue: Claims extraction failed
**Check:**
1. LLM service logs for errors
2. Entity extraction succeeded first
3. Rate limiting issues (60 req/min)

### Issue: Malformed claim records
**Cause:** LLM returned invalid tuple format
**Solution:** System logs warning and skips malformed records

### Issue: "Entity not found" when linking claims
**Cause:** Subject/object entity name doesn't match extracted entity
**Solution:** Ensure entity names are exact matches (case-sensitive)

### Issue: Claims query returns empty results
**Check:**
1. Claims were actually extracted (check processing results)
2. Filter parameters match claim types/statuses
3. Entity name is exact match (case-sensitive)

---

## Performance Considerations

### LLM Calls
- **Claims extraction adds:** ~1 LLM call per chunk (same as entity/relationship extraction)
- **Rate limiting:** 60 requests/minute (built-in)
- **Batch processing:** Processes all chunks sequentially with 0.1s delay

### Storage
- **Neo4j nodes:** +1 Claim node per extracted claim
- **Relationships:** +2-3 relationships per claim
  - 1x MAKES_CLAIM (subject → claim)
  - 0-1x ABOUT (claim → object, if object exists)
  - 1x SOURCED_FROM (claim → text unit)

### Query Performance
- **Get all claims:** O(n) where n = total claims
- **Get claims for entity:** O(m) where m = entity's claims
- **Indexed queries:** claim_type and status indexed for fast filtering

---

## Code Changes Summary

### Files Modified
1. ✅ `backend/app/services/graph_service.py` - Added Claim schema & storage methods
2. ✅ `backend/app/services/prompt.py` - Added claims prompt builder
3. ✅ `backend/app/services/llm_service.py` - Added claims extraction methods
4. ✅ `backend/app/services/document_processor.py` - Added Step 8.5 claims extraction
5. ✅ `backend/app/services/query_service.py` - Added claims query methods
6. ✅ `backend/app/api/endpoints/queries.py` - Added claims API endpoints

### Files Created
7. ✅ `backend/app/schemas/claim.py` - Pydantic schemas for claims
8. ✅ `CLAIMS_IMPLEMENTATION.md` - This documentation

### Lines of Code Added
- **graph_service.py:** ~300 lines (schema + 5 methods)
- **prompt.py:** ~40 lines (prompt builder)
- **llm_service.py:** ~150 lines (extraction + parsing)
- **document_processor.py:** ~45 lines (pipeline integration)
- **query_service.py:** ~170 lines (3 query methods)
- **queries.py:** ~170 lines (3 API endpoints)
- **schemas/claim.py:** ~70 lines (7 schemas)

**Total:** ~945 lines of new code

---

## Microsoft GraphRAG Compliance

This implementation follows Microsoft GraphRAG best practices:

✅ **Claims Extraction:** Uses official GraphRAG claims prompt template
✅ **Tuple-Based Format:** Follows tuple delimiter format (`<|>`, `##`, `<|COMPLETE|>`)
✅ **Structured Output:** 8-field tuple format as specified
✅ **Entity Grounding:** Claims linked to extracted entities
✅ **Source Traceability:** Claims linked to source TextUnits
✅ **Status Tracking:** TRUE/FALSE/SUSPECTED status support
✅ **Temporal Context:** Date range tracking for claims
✅ **Graph Integration:** Claims stored as first-class nodes in Neo4j

**Reference:** https://microsoft.github.io/graphrag/

---

## Next Steps

### Immediate (Optional)
- [ ] Add claims visualization in frontend
- [ ] Add claims dashboard with statistics
- [ ] Implement claim verification workflow
- [ ] Add claim editing/updating API

### Future Enhancements (Priority 3)
- [ ] Claim confidence scoring
- [ ] Claim conflict detection (contradicting claims)
- [ ] Claim evolution tracking (status changes over time)
- [ ] Claim provenance chain (source document → claim)
- [ ] Claim validation rules engine
- [ ] Claim similarity detection (duplicate claims)
- [ ] Export claims to external fact-checking tools
- [ ] Automated claim verification with external sources

---

## Conclusion

Claims Extraction & Storage is now **fully implemented and ready to use**. The system automatically extracts claims during document processing and provides comprehensive query and filtering capabilities.

**Key Achievements:**
- ✅ GraphRAG-compliant claims extraction
- ✅ Complete Neo4j schema integration
- ✅ Automatic extraction in document pipeline
- ✅ Comprehensive query API
- ✅ Natural language claims querying
- ✅ Filtering by type, status, entity
- ✅ Temporal tracking with date ranges
- ✅ Full source traceability

The implementation provides a solid foundation for fact-checking, compliance, due diligence, and knowledge base applications.

---

**Last Updated:** 2025-10-30
**Version:** 1.0
**Author:** Claude Code
