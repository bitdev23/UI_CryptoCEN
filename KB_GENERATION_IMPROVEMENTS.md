# KB-Grounded Generation Fixes — Implementation Summary

## Problem Statement
Users uploaded knowledge base PDFs (e.g., Crypto_Web3_Knowledge_Base) but generated LinkedIn posts were generic and didn't reference uploaded KB content. Example: When asked to generate a post about "How automated market makers (AMMs) work and Constant Product Formula", the system returned generic "DeFi yields are unsustainable" text instead of KB-grounded content about AMM mechanics.

**User's concern:** "If it gives such result then how do we become the multi billion saas?"

## Root Causes Identified

### 1. Overly Conservative Search Thresholds
- **Vector similarity threshold**: 0.68 was too high, filtering out marginal but relevant matches
- **Retrieval candidates (k)**: Only fetched 4 hits per query, limiting coverage
- **Keyword weight**: Too much emphasis on keyword overlap (0.3) vs semantic similarity (0.7)

### 2. Overly Strict Grounding Classification
- **FULL grounding requirement**: avg_sim ≥ 0.77 with 2+ hits ≥ 0.78 (almost impossible to reach)
- **PARTIAL grounding requirement**: avg_sim ≥ 0.68 (still very restrictive)
- **Result**: System would classify most KB searches as UNGROUNDED, telling LLM to ignore KB

### 3. Limited Query Expansion
- Only 3-4 retrieval queries, missing domain and use-case variations
- Example: Searching for "AMM" wouldn't try industry+role combos or goal-based queries

### 4. Insufficient KB Context in Prompt
- Only top 3 KB hits included (should be 5)
- Each chunk truncated to 900 chars (should be 1200 for complex topics)
- PARTIAL grounding prompt didn't encourage active KB usage

### 5. No Debugging Visibility
- Zero logging in KB retrieval pipeline
- Impossible to diagnose why posts were generic

## Solutions Implemented

### 1. Lowered KB Search Thresholds (app.py ~6282)

**File**: app.py, line ~6282

```python
# BEFORE
hits = rag.hybrid_search(
    rq, k=4,
    match_threshold=0.68,
    file_ids=file_id_arg,
    vector_weight=0.7,
    keyword_weight=0.3,
)

# AFTER (IMPROVED)
hits = rag.hybrid_search(
    rq, k=6,  # Increased from 4 to 6
    match_threshold=0.50,  # Lowered from 0.68 to 0.50
    file_ids=file_id_arg,
    vector_weight=0.75,  # Adjusted from 0.7
    keyword_weight=0.25,  # Adjusted from 0.3
)
```

**Impact**:
- More lenient threshold (0.50) captures weaker semantic matches
- More candidates (k=6) increases chance of finding relevant content
- Better weight balance: semantic (0.75) > keyword (0.25)

### 2. Improved Grounding Classification (app.py ~5515)

**File**: app.py, line ~5515

```python
# BEFORE
- FULL: avg_sim >= 0.77 AND 2+ hits >= 0.78
- PARTIAL: avg_sim >= 0.68
- NONE: default

# AFTER (IMPROVED)
- FULL: avg_sim >= 0.70 AND 2+ hits >= 0.70  # Lowered from 0.77/0.78
- PARTIAL: avg_sim >= 0.55  # Lowered from 0.68
- NONE: default
```

**Impact**:
- More posts will be classified as PARTIAL (with some KB support)
- Fewer posts fall through to INSIGHT-ONLY (no KB) mode
- LLM will be instructed to use KB content more often

### 3. Enhanced Query Expansion (app.py ~5435)

**File**: app.py, line ~5435

Added 2 new query variations:
- **Industry + Role alone**: Catches KB organized by professional domain
- **Topic + Goal**: Catches KB organized by business objective

Total queries: 3-4 → 4-6 variations

**Example**:
- Topic: "AMM Constant Product Formula"
- Industry: "Crypto"
- Role: "CEO"
- Goal: "Build Authority"

**Old queries**:
1. "AMM Constant Product Formula"
2. "AMM Constant Product Formula in crypto"
3. "AMM Constant Product Formula from CEO perspective"
4. "crypto CEO build authority AMM Constant Product Formula"

**New queries** (adds):
5. "crypto CEO" (domain-focused)
6. "AMM Constant Product Formula for build authority" (goal-focused)

### 4. Increased KB Context Injection (app.py ~6354)

**File**: app.py, line ~6354

```python
# BEFORE
for idx, hit in enumerate(kb_hits[:3], start=1):  # Top 3 only
    snippets.append(f"[{idx}] Source: {src}\n{doc_text[:900]}")  # 900 chars

# AFTER (IMPROVED)
for idx, hit in enumerate(kb_hits[:5], start=1):  # Top 5 now
    snippets.append(f"[{idx}] Source: {src}\n{doc_text[:1200]}")  # 1200 chars
```

**Impact**:
- Richer context passed to LLM (5 chunks × 1200 chars = 6KB vs old 3 × 900 = 2.7KB)
- Better for complex topics like crypto mechanisms, formulas, technical concepts

### 5. Improved PARTIAL Grounding Prompt (app.py ~5560)

**File**: app.py, line ~5560

Enhanced PARTIAL mode instructions:
- Added "USE THEM ACTIVELY" to encourage KB reference
- Added specific examples of how to weave KB concepts
- Removed passive "use with care" language
- Added "Actively weave KB concepts into the post"

**Before**:
```
"You have SOME relevant KB excerpts but coverage is incomplete."
```

**After**:
```
"The KB excerpts above are your primary source for this topic. USE THEM ACTIVELY..."
```

### 6. Added Debug Logging (app.py ~6325-6360)

**File**: app.py, lines ~6325-6360

Added 4 key logging statements:

1. **After hybrid search**: Number of queries, total hits
   ```python
   logger.info('KB retrieval: searched %d queries, found %d hybrid hits')
   ```

2. **Top 5 similarities after retrieval**:
   ```python
   logger.info('KB hit similarities (top 5): %s')
   ```

3. **After filtering and reranking**:
   ```python
   logger.info('KB final state: %d chunks after filtering')
   ```

4. **Grounding classification details**:
   ```python
   logger.info('Grounding level: %s (avg_sim=%.3f, hits=%d, kb_mode=%s, kb_used=%s)')
   ```

**Impact**:
- Operators can now see exactly what KB hits are being found
- Can diagnose why grounding is PARTIAL vs NONE
- Can measure effectiveness of threshold changes

## Testing & Validation

### Smoke Test Results
✅ All 6 AI provider routing tasks pass (generate, rewrite, repurpose, style_clone, analysis, evaluate)
✅ No syntax errors in modified code
✅ Generation endpoint functional

### Expected Behavior After Fixes

**For Crypto/AMM Topic Generation**:
1. User uploads crypto KB PDF with AMM content
2. User requests: "AMM and Constant Product Formula post"
3. **Old system**: Finds 0 KB hits → UNGROUNDED → generic post
4. **New system**: Finds 5 KB hits with avg_sim=0.65 → PARTIAL → KB-grounded post

**Post quality change**:
- **Old**: "Explore the world of DeFi yields and how they impact your portfolio..."
- **New**: "Automated Market Makers (AMMs) use a constant product formula (x×y=k) to determine prices..."

## Files Modified

1. **app.py** (main changes)
   - `_classify_grounding_level()`: Lowered thresholds
   - `_expand_retrieval_queries()`: Added 2 new query types
   - `_build_grounding_prompt_rules()`: Enhanced PARTIAL mode instructions
   - `/api/generate-preview` endpoint:
     - Hybrid search parameters (match_threshold, k, weights)
     - KB context extraction (top 5 hits, 1200 chars)
     - Added debug logging (4 new logger.info calls)

2. **Test utilities created**
   - `test_kb_search.py`: Diagnostic tool for KB testing
   - `test_crypto_amm_kb.py`: Specific crypto/AMM test

## Deployment Checklist

- [x] Changes compile without errors
- [x] Smoke tests pass
- [x] No breaking changes to API
- [x] Backward compatible (uses same KB files)
- [x] Debug logging doesn't impact performance
- [ ] Test with real user KB (requires user ID)
- [ ] Monitor logs for grounding level distribution
- [ ] Measure post quality improvement (user feedback)

## Monitoring & Next Steps

### What to Monitor
1. **Grounding level distribution** (logs):
   - % of posts with FULL vs PARTIAL vs UNGROUNDED
   - Target: 40%+ FULL+PARTIAL for knowledge-based users

2. **KB hit statistics** (logs):
   - Average similarity scores
   - Number of hits per query
   - Filter rate (% dropped during quality check)

3. **User feedback**:
   - Are posts more specific and KB-grounded?
   - Do they reference uploaded knowledge?

### If Still Not Working
1. **Verify KB was indexed**:
   - Check `/api/knowledge-base-status` response
   - Confirm `trained: true` and chunk count > 0

2. **Check embedding model capacity**:
   - Current: all-MiniLM-L6-v2 (384 dims, lightweight)
   - Consider: all-mpnet-base-v2 (768 dims, better quality)
   - Note: Requires re-embedding all KBs

3. **Increase KB context further**:
   - Top 5 hits → Top 7 hits
   - 1200 chars → 1500 chars per chunk

4. **Add semantic query rewriting**:
   - Use LLM to expand queries with synonyms
   - Example: "AMM" → "automated market makers, liquidity pools, DEX"

## Summary

These changes make the KB-grounded generation system more practical and effective by:
- **Lowering barriers** to finding relevant KB content (0.68 → 0.50 threshold)
- **Expanding search** to find content via multiple query angles (3-4 → 4-6 queries)
- **Improving prompt** to actively encourage KB usage (especially in PARTIAL mode)
- **Providing visibility** via debug logging to diagnose issues

Expected outcome: Posts will be more specific, reference user knowledge bases, and be grounded in actual content rather than generic insights.
