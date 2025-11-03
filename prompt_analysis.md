# Phân tích Prompt Templates - So sánh với GraphRAG chính thức

## Tổng quan

Hệ thống của bạn đã triển khai các prompt templates dựa trên Microsoft GraphRAG. Dưới đây là phân tích chi tiết về mức độ tuân thủ và các điểm khác biệt.

---

## 1. GRAPH_EXTRACTION_PROMPT_TEMPLATE

### ✅ Điểm phù hợp:

1. **Cấu trúc chính xác**: Prompt của bạn (dòng 30-150) khớp **hoàn toàn** với template GraphRAG gốc
2. **4 bước xử lý**: Giữ nguyên quy trình chuẩn:
   - Bước 1: Nhận diện entities
   - Bước 2: Nhận diện relationships
   - Bước 3: Định dạng output
   - Bước 4: Completion signal
3. **Ví dụ đầy đủ**: Giữ nguyên 3 ví dụ chuẩn từ GraphRAG:
   - Example 1: ORGANIZATION, PERSON (Central Institution, Martin Smith)
   - Example 2: ORGANIZATION (TechGlobal, Vision Holdings)
   - Example 3: GEO, PERSON (hostage exchange scenario)
4. **Delimiters**: Sử dụng đúng các delimiters chuẩn:
   - `tuple_delimiter`: `|||` (DEFAULT_TUPLE_DELIMITER)
   - `record_delimiter`: `\n` (DEFAULT_RECORD_DELIMITER)
   - `completion_delimiter`: `<COMPLETE>` (DEFAULT_COMPLETION_DELIMITER)

### 🎯 Điểm đánh giá:

**10/10** - Prompt này hoàn toàn chuẩn GraphRAG, không cần sửa đổi gì.

---

## 2. EXTRACT_CLAIMS_PROMPT_TEMPLATE

### ✅ Điểm phù hợp:

1. **Cấu trúc đầy đủ**: Template (dòng 158-209) tuân thủ format GraphRAG gốc
2. **Claim attributes**: Đầy đủ các trường bắt buộc:
   - Subject Entity, Object Entity
   - Claim Type, Claim Status (TRUE/FALSE/SUSPECTED)
   - Claim Date (ISO-8601 format)
   - Claim Description, Claim Source Text
3. **Ví dụ chuẩn**: 2 examples từ GraphRAG về bid rigging và corruption
4. **Format chính xác**: Sử dụng tuple format đúng chuẩn

### 🎯 Điểm đánh giá:

**10/10** - Claim extraction prompt hoàn toàn chuẩn GraphRAG.

---

## 3. COMMUNITY_REPORT_PROMPT_TEMPLATE

### ✅ Điểm phù hợp:

1. **5 sections bắt buộc**: Đầy đủ theo chuẩn (dòng 255-403):
   - TITLE
   - SUMMARY
   - IMPACT SEVERITY RATING (0-10)
   - RATING EXPLANATION
   - DETAILED FINDINGS (5-10 insights)
2. **JSON output format**: Đúng cấu trúc yêu cầu
3. **Grounding rules**: Triển khai đầy đủ:
   - Data references: `[Data: <dataset name> (record ids)]`
   - Max 5 record IDs, dùng "+more" khi cần
   - Không cho phép thông tin không có evidence
4. **Example đầy đủ**: Ví dụ "Verdant Oasis Plaza and Unity March" giống GraphRAG gốc

### ⚠️ Điểm khác biệt:

1. **Trùng lặp nội dung**: Bạn có đoạn từ dòng 360-401 lặp lại y hệt phần instructions ở dòng 258-304. Điều này **không cần thiết** và làm prompt dài hơn.

### 🎯 Điểm đánh giá:

**9/10** - Rất tốt, chỉ cần loại bỏ phần trùng lặp.

---

## 4. COMMUNITY_REPORT_TEXT_PROMPT_TEMPLATE

### ✅ Điểm phù hợp:

1. **Phiên bản mở rộng**: Template này (dòng 405-500) là variant của community report
2. **Thêm DATE_RANGE**: Field mới cho phạm vi thời gian của text units
3. **Example chi tiết**: Enron compliance example rất phù hợp
4. **Grounding với date ranges**: Format `[Data: Sources (2, 3), Date_Range ((2000, 01, 01), (2000, 07, 12))]`

### 🎯 Điểm đánh giá:

**10/10** - Đây là enhanced version phù hợp với use case của bạn.

---

## 5. SUMMARIZE_DESCRIPTIONS_PROMPT_TEMPLATE

### ✅ Điểm phù hợp:

1. **Template đơn giản**: Khớp 100% với GraphRAG gốc (dòng 502-516)
2. **Yêu cầu rõ ràng**:
   - Concatenate multiple descriptions
   - Resolve contradictions
   - Third person perspective
   - Include entity names
   - Limit to {max_length} words

### 🎯 Điểm đánh giá:

**10/10** - Hoàn toàn chuẩn.

---

## 6. MAP_REDUCE Prompts (Global Search)

### ✅ Điểm mới:

Bạn có thêm 2 prompts cho Map-Reduce pattern (dòng 954-1054):

1. **MAP_REDUCE_BATCH_SUMMARY_PROMPT**: Summarize batches of communities
2. **MAP_REDUCE_FINAL_SYNTHESIS_PROMPT**: Synthesize final answer

### 📊 Đánh giá:

**Tốt** - Đây là implementation chuẩn cho Global Search theo Microsoft GraphRAG. Các prompt này:
- Tuân thủ map-reduce pattern của GraphRAG
- JSON output format rõ ràng
- Có confidence scoring và limitations tracking

---

## 7. Helper Functions

### ✅ Các hàm đã có:

- `build_graph_extraction_prompt()` ✓
- `build_claim_extraction_prompt()` ✓
- `build_community_report_prompt()` ✓
- `build_community_report_from_text_units_prompt()` ✓
- `build_description_summarization_prompt()` ✓
- `build_map_reduce_batch_summary_prompt()` ✓
- `build_map_reduce_final_synthesis_prompt()` ✓

### ⚠️ Hàm đặc biệt:

**`_append_relationship_focus()`** (dòng 555-589):
- Đây là custom modification để extract **chỉ relationships** khi entities đã có sẵn
- Thêm instruction để skip entity extraction
- **Rất hữu ích** cho optimization, giảm token usage

---

## 8. Additional Prompts (Custom Extensions)

Bạn có thêm một số prompts **không có** trong GraphRAG gốc:

### 🆕 Custom prompts:

1. **`build_few_shot_entity_prompt()`** (dòng 765-782)
2. **`build_coreference_prompt()`** (dòng 785-805)
3. **`build_attribute_extraction_prompt()`** (dòng 808-827)
4. **`build_event_extraction_prompt()`** (dòng 830-851)
5. **`build_multi_perspective_prompt()`** (dòng 854-882)
6. **`build_query_classification_prompt()`** (dòng 921-931)
7. **`build_contextual_answer_prompt()`** (dòng 934-947)

### 📊 Đánh giá custom prompts:

**Tốt** - Đây là các extensions hợp lý cho:
- Advanced entity resolution (coreference)
- Query classification (local/global/hybrid)
- Multi-perspective reasoning (ToG compatibility)
- Contextual QA

---

## Tổng kết

### ✅ Những gì đã chuẩn GraphRAG:

1. ✅ **GRAPH_EXTRACTION_PROMPT**: 100% chuẩn
2. ✅ **EXTRACT_CLAIMS_PROMPT**: 100% chuẩn
3. ✅ **COMMUNITY_REPORT_PROMPT**: 95% chuẩn (có trùng lặp nhỏ)
4. ✅ **SUMMARIZE_DESCRIPTIONS_PROMPT**: 100% chuẩn
5. ✅ **MAP_REDUCE prompts**: Chuẩn theo pattern GraphRAG
6. ✅ **Helper functions**: Đầy đủ và đúng

### 🎯 Điểm tổng thể: **9.5/10**

### 🔧 Khuyến nghị sửa đổi:

#### 1. Loại bỏ trùng lặp trong COMMUNITY_REPORT_PROMPT_TEMPLATE

**Dòng cần xóa: 360-401**

```python
# XÓA đoạn này (trùng lặp):
"""
The report should include the following sections:

- TITLE: community's name that represents its key entities...
...
Output:"""
```

Vì đoạn này đã có ở dòng 258-304 rồi.

#### 2. Verify delimiters consistency

Kiểm tra xem trong các service files có dùng đúng delimiters không:

```python
# Chuẩn GraphRAG:
DEFAULT_TUPLE_DELIMITER = "|||"
DEFAULT_RECORD_DELIMITER = "\n"
DEFAULT_COMPLETION_DELIMITER = "<COMPLETE>"
```

#### 3. Thêm docstrings cho custom prompts

Các custom prompts nên có docstring giải thích rõ chúng là extensions, không phải GraphRAG gốc:

```python
def build_query_classification_prompt(query: str) -> str:
    """
    Create prompt for classifying query type.

    NOTE: This is a CUSTOM extension, not part of Microsoft GraphRAG.
    Used for routing queries to appropriate search strategies.
    """
    ...
```

---

## Kết luận

Hệ thống prompt của bạn **rất chuẩn theo GraphRAG**. Các điểm chính:

1. ✅ Core prompts (extraction, claims, community reports) hoàn toàn tuân thủ Microsoft GraphRAG
2. ✅ Map-Reduce implementation đúng pattern cho Global Search
3. ✅ Helper functions đầy đủ và chính xác
4. ✅ Custom extensions (query classification, coreference, etc.) là additions hợp lý
5. ⚠️ Chỉ có 1 issue nhỏ: trùng lặp trong community report prompt

**Không cần refactor lớn**, chỉ cần cleanup nhỏ theo khuyến nghị trên.
