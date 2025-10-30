# 🔌 API Usage Guide - GraphRAG Global Search

## Overview

API endpoint mới cho GraphRAG Global Search: `/api/queries/global`

---

## Endpoint: POST /api/queries/global

### Description
Process global/holistic queries using community summaries (Microsoft GraphRAG methodology).

Best for:
- Dataset-wide questions
- High-level insights
- Thematic analysis
- Holistic understanding

### Authentication
Requires Bearer token (JWT) in Authorization header.

---

## Request Format

### Headers
```
Authorization: Bearer <your_jwt_token>
Content-Type: application/json
```

### Body
```json
{
  "query": "What are the main themes in this dataset?"
}
```

---

## Response Format

### Success Response (200 OK)
```json
{
  "id": "uuid-here",
  "status": "success",
  "query": "What are the main themes in this dataset?",
  "query_type": "global",
  "num_communities": 3,
  "answer": "Based on the community analysis across 3 detected communities with 45 entities, the main themes are: 1) Technology and Innovation - focusing on AI/ML development...",
  "context": "📊 **Dataset Overview**: 45 entities across 3 communities\n\n🏘️ **Community 42** (Level 0):\n   • Size: 25 entities\n   • Significance: HIGH\n   • Summary: This community...",
  "confidence_score": "0.85",
  "citations": [
    "Community 42 (25 entities)",
    "Community 15 (12 entities)",
    "Community 8 (8 entities)"
  ]
}
```

### Error Response (500 Internal Server Error)
```json
{
  "detail": "Community summaries not yet generated. Please process documents first."
}
```

---

## Example Usage

### cURL Example

```bash
# 1. Login first
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}' \
  | jq -r '.access_token')

# 2. Send global query
curl -X POST http://localhost:8000/api/queries/global \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main themes in this dataset?"
  }' | jq
```

### Python Example

```python
import requests

# 1. Login
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "testuser", "password": "password123"}
)
token = login_response.json()["access_token"]

# 2. Global query
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

query_data = {
    "query": "What are the main themes in this dataset?"
}

response = requests.post(
    "http://localhost:8000/api/queries/global",
    headers=headers,
    json=query_data
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Communities analyzed: {result['num_communities']}")
print(f"Confidence: {result['confidence_score']}")
```

### JavaScript/TypeScript Example

```typescript
// 1. Login
const loginResponse = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'testuser',
    password: 'password123'
  })
});

const { access_token } = await loginResponse.json();

// 2. Global query
const queryResponse = await fetch('http://localhost:8000/api/queries/global', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: 'What are the main themes in this dataset?'
  })
});

const result = await queryResponse.json();
console.log('Answer:', result.answer);
console.log('Communities:', result.num_communities);
console.log('Confidence:', result.confidence_score);
```

---

## Sample Queries

### 1. Thematic Analysis
```json
{
  "query": "What are the main themes discussed in the documents?"
}
```

### 2. Dataset Summary
```json
{
  "query": "Give me a high-level summary of what this dataset is about"
}
```

### 3. Key Topics
```json
{
  "query": "What are the most important topics covered?"
}
```

### 4. Comparative Analysis
```json
{
  "query": "What are the common patterns across all documents?"
}
```

### 5. Domain Overview
```json
{
  "query": "Describe the overall domain and focus areas of this knowledge base"
}
```

---

## Response Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique query ID (UUID) |
| `status` | string | "success" or "error" |
| `query` | string | Original query text |
| `query_type` | string | "global" (fixed for this endpoint) |
| `num_communities` | integer | Number of communities analyzed |
| `answer` | string | Generated answer from LLM |
| `context` | string | Formatted community summaries used |
| `confidence_score` | string | Confidence level (0.0-1.0) |
| `citations` | array | List of community sources |

---

## Error Codes

| Code | Error | Solution |
|------|-------|----------|
| 400 | Query cannot be empty | Provide query text |
| 400 | Query too long (max 1000 characters) | Shorten query |
| 401 | Unauthorized | Check authentication token |
| 500 | Community summaries not yet generated | Process documents first |
| 500 | Failed to retrieve global context | Check Neo4j connection |

---

## Comparison: Regular Query vs Global Query

### Regular Query (`POST /api/queries`)
```json
{
  "query": "What is AI?",
  "hop_limit": 1,
  "document_id": "specific-doc-id"  // Optional
}
```
**Best for**:
- Specific entity-based questions
- Document-specific queries
- Detail-oriented questions
- Local context retrieval

**Uses**: Local/Community search (1-2 hop traversal)

---

### Global Query (`POST /api/queries/global`)
```json
{
  "query": "What are the main themes in this dataset?"
}
```
**Best for**:
- Dataset-wide questions
- High-level insights
- Thematic analysis
- Holistic understanding

**Uses**: Global search with community summaries

---

## Performance

### Expected Response Times
- Small dataset (<50 entities): ~2-3 seconds
- Medium dataset (50-200 entities): ~3-5 seconds
- Large dataset (200+ entities): ~5-10 seconds

### Optimization Tips
1. Ensure community summaries are pre-generated during document processing
2. Use Redis caching (if implemented)
3. Limit query length for faster processing

---

## Integration with Frontend

### React/Next.js Example

```typescript
// hooks/useGlobalQuery.ts
import { useState } from 'react';

export const useGlobalQuery = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const executeGlobalQuery = async (query: string) => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      
      const response = await fetch('/api/queries/global', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
      });

      if (!response.ok) {
        throw new Error('Query failed');
      }

      const data = await response.json();
      setResult(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { executeGlobalQuery, loading, result, error };
};

// Usage in component
function GlobalSearchComponent() {
  const { executeGlobalQuery, loading, result } = useGlobalQuery();

  const handleSubmit = async (query: string) => {
    const response = await executeGlobalQuery(query);
    console.log('Answer:', response.answer);
  };

  return (
    <div>
      {loading && <Spinner />}
      {result && (
        <div>
          <h3>Answer</h3>
          <p>{result.answer}</p>
          
          <h4>Communities Analyzed: {result.num_communities}</h4>
          <p>Confidence: {result.confidence_score}</p>
          
          <h4>Sources</h4>
          <ul>
            {result.citations.map((citation, i) => (
              <li key={i}>{citation}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

---

## Testing

### Postman Collection

```json
{
  "info": {
    "name": "GraphRAG Global Query",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Login",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/auth/login",
        "body": {
          "mode": "raw",
          "raw": "{\"username\":\"testuser\",\"password\":\"password123\"}"
        }
      }
    },
    {
      "name": "Global Query",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/queries/global",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{token}}"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"query\":\"What are the main themes?\"}"
        }
      }
    }
  ]
}
```

---

## Best Practices

1. **Use Global Query for**:
   - "What are the main themes?"
   - "Summarize the dataset"
   - "What topics are covered?"
   - "Give me an overview"

2. **Use Regular Query for**:
   - "What is entity X?"
   - "How does Y relate to Z?"
   - "Tell me about document D"

3. **Query Tips**:
   - Keep queries under 1000 characters
   - Be specific about what high-level insight you want
   - Use open-ended questions for better results

4. **Performance**:
   - Process documents before querying
   - Ensure community summaries are generated
   - Monitor response times and adjust as needed

---

## Troubleshooting

### Issue: "Community summaries not yet generated"
**Solution**: Process documents first
```bash
# Upload and process a document through the API or UI
# Community summaries are generated automatically
```

### Issue: Slow response times
**Solution**: Check community summary availability
```bash
curl -X GET http://localhost:8000/api/queries/graph/stats \
  -H "Authorization: Bearer $TOKEN"
```

### Issue: Empty or generic answers
**Solution**: 
1. Ensure documents have been processed
2. Check if communities were detected
3. Verify summaries were generated
4. Run test script to validate

---

## Related Endpoints

- `POST /api/queries` - Regular entity-based query
- `GET /api/queries/{query_id}` - Retrieve query by ID
- `GET /api/queries` - List all queries for user
- `GET /api/queries/graph/stats` - Get graph statistics
- `POST /api/queries/batch-queries` - Batch query processing

---

## Version History

- **v1.0** (2025-10-30): Initial release with GraphRAG Global Search support

---

## Support

For issues or questions, check:
- `GRAPHRAG_IMPLEMENTATION_COMPLETED.md` - Implementation details
- `QUICK_START_GRAPHRAG.md` - Quick start guide
- `test_graphrag_fixes.py` - Validation tests

Happy querying! 🚀

