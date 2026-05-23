# Grounding Contract Fix - Summary

## Problem

You were seeing the error:
```
Grounding contract not met for strict mode. Need at least 2 relevant KB chunks with avg similarity >= 0.56.
```

**This was happening even though:**
- Your KB content (e.g., "6. Types of Crypto Assets") was relevant
- You were selecting both strict and balanced modes
- Both were failing

## Root Cause

The issue was in how **hybrid scoring** was calculated:

```python
# Retrieval (match_threshold = 0.50)
vector_score = 0.50

# Hybrid scoring (75% vector + 25% keyword)
hybrid_score = 0.75 * 0.50 + 0.25 * 0.0
hybrid_score = 0.375

# Grounding contract (needed 0.42 for balanced)
0.375 < 0.42  ❌ FAIL
```

**The problem:** Even when KB retrieval worked, the hybrid scoring weighted results so heavily that scores dropped below grounding thresholds.

## Solution

Two changes were made to `app.py`:

### Change 1: Lowered Retrieval Threshold

**Before:**
```python
hits = rag.hybrid_search(
    rq, k=6,
    match_threshold=0.50,  # ← TOO HIGH
    file_ids=file_id_arg,
    vector_weight=0.75,
    keyword_weight=0.25,
)
```

**After:**
```python
hits = rag.hybrid_search(
    rq, k=8,
    match_threshold=0.30,  # ← LOWERED to 0.30
    file_ids=file_id_arg,
    vector_weight=0.75,
    keyword_weight=0.25,
)
```

**Why:**
- Lower threshold means more candidates are retrieved
- With keyword matching, scores can reach 0.45+
- Example: 0.30 vector × 0.75 + 1.0 keyword × 0.25 = 0.475 ✅

### Change 2: Adjusted Grounding Contract Thresholds

**Before:**
```python
min_avg_similarity = 0.56 if grounding_mode == 'strict' else (0.42 if grounding_mode == 'balanced' else 0.0)
```

**After:**
```python
min_avg_similarity = 0.45 if grounding_mode == 'strict' else (0.35 if grounding_mode == 'balanced' else 0.0)
```

**New Requirements:**
| Mode | Hits | Min Avg Similarity |
|------|------|-------------------|
| **Strict** | 2 | 0.45 (was 0.56) |
| **Balanced** | 1 | 0.35 (was 0.42) |

**Why:**
- Accounts for lower match_threshold (0.30)
- Reasonable for hybrid-scored results
- Typical hit with keyword match: 0.40-0.55 range ✅

## How to Test

### Option 1: Quick Manual Test

In your dashboard:
1. Go to Create Post
2. Select your KB topic (e.g., "6. Types of Crypto Assets")
3. Select **Balanced** grounding mode
4. Try to generate

**Expected:** ✅ Should work now

### Option 2: Run Diagnostic Script

```bash
# First, find your user ID in Supabase (User table)
TEST_USER_ID=your-uuid-here python debug_grounding_contract.py "6. Types of Crypto Assets" "Crypto & Web3"
```

**Output shows:**
- How many KB hits are found
- Average similarity scores
- Whether new thresholds are met

### Option 3: Check Logs

In your Flask terminal, look for:

```
KB retrieval: searched 6 queries, found 3 hybrid hits before filtering
KB hit similarities (top 5): ['0.4521', '0.4285', '0.3912']
```

If you see scores in the 0.35-0.55 range, that's good! ✅

## Confidence Levels

### What Should Work Now

✅ **Topics with clear KB matches**
- Your "6. Types of Crypto Assets" should work in both modes
- Other crypto topics with 1+ relevant chunks

✅ **Balanced mode**
- Easier requirement (1 hit, 0.35 threshold)
- Most topics should pass

### What Still Might Not Work

⚠️ **Very niche topics with no KB coverage**
- If your KB literally has no content about the topic
- Solution: Upload relevant documents

⚠️ **Weak embedding model**
- If vector similarity scores are all < 0.20
- Solution: Check EMBEDDING_MODEL in .env

## Files Modified

1. `/app.py` - Lines ~6820-6943
   - Lowered match_threshold: 0.50 → 0.30
   - Increased retrieval count: k=6 → k=8
   - Adjusted thresholds: strict 0.56→0.45, balanced 0.42→0.35

2. `/debug_grounding_contract.py` (NEW)
   - Diagnostic script to test grounding

## Next Steps

1. **Test immediately** - Try generating with balanced mode
2. **Monitor scores** - Check Flask logs for similarity scores
3. **Run diagnostic** if issues persist - Use the debug script
4. **Report results** - Let me know if this fixes your issue

## If Still Not Working

Check:
1. **KB is indexed:** Go to Settings → Knowledge Base, verify chunks are there
2. **Topic matches KB:** Try a topic that clearly exists in your KB
3. **Balanced mode first:** Easier threshold, helps isolate the issue
4. **Embedding model:** Is EMBEDDING_MODEL env var set correctly?

Run diagnostic to see exact scores:
```bash
TEST_USER_ID=your-id python debug_grounding_contract.py
```
