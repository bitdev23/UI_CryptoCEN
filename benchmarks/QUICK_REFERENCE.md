# Quick Reference: Exporting Real Posts

## TL;DR - 3 Commands

```bash
# 1. Export your real posts
python benchmarks/export_real_generations.py --limit 31

# 2. Test locally
python benchmarks/run_generation_quality_bench.py \
  --suite benchmarks/generation_quality_suite.sample.json \
  --responses benchmarks/results/latest_generation_outputs.json \
  --min-pass-rate 70

# 3. Push to GitHub (CI runs automatically)
git add benchmarks/results/latest_generation_outputs.json
git commit -m "Add real generation outputs for CI validation"
git push origin main
```

Done! GitHub Actions will validate and show results.

---

## What Happens At Each Step

### Step 1: Export
```bash
$ python benchmarks/export_real_generations.py --limit 31

============================================================
EXPORTING REAL GENERATION OUTPUTS FOR BENCHMARK
============================================================

✅ Loaded 31 posts from data/posts.json
✅ Exported 31 posts to benchmarks/results/latest_generation_outputs.json

Next steps:
  git add benchmarks/results/latest_generation_outputs.json
  git commit -m 'Add real generation outputs for CI validation'
  git push origin main
============================================================
```

**Result**: File `benchmarks/results/latest_generation_outputs.json` created with your posts

### Step 2: Test
```bash
$ python benchmarks/run_generation_quality_bench.py ...

{
  "suite_name": "global_platform_quality_smoke",
  "total_cases": 31,
  "passed_cases": 15,
  "failed_cases": 16,
  "pass_rate": 48.4,
  "avg_score": 76.3
}
```

**Result**: You see quality score (your actual pass rate)

### Step 3: Push
```bash
$ git push origin main

✅ GitHub Actions detected change
✅ CI started automatically
✅ Runs benchmark with your real posts
✅ Generates report artifact
```

**Result**: GitHub shows ✅ or ❌ in Actions tab

---

## Export Script Options

```bash
# Export from local JSON (default)
python benchmarks/export_real_generations.py --limit 31

# Export more posts
python benchmarks/export_real_generations.py --limit 50

# Export from Supabase
python benchmarks/export_real_generations.py --from-supabase --limit 31

# Custom output location
python benchmarks/export_real_generations.py \
  --output my_posts.json \
  --limit 31

# Just check without exporting
python benchmarks/export_real_generations.py --help
```

---

## What You're Testing

When you export + push real posts:

```
Before:
├─ Sample posts → 100% pass rate ✅
│  (Synthetic, hand-curated, always passes)

After:
├─ Real posts → ??? pass rate 🤔
│  (Your actual generation quality)
│
├─ If 80%+: "Your generation is solid"
├─ If 60-80%: "Good, room for improvement"
├─ If <60%: "Need to tune generation prompt"
```

---

## Expected Results

### Crypto-Focused Platform
```
Real posts: Mostly crypto
Benchmark suite: Multi-industry
Expected pass rate: 20-40%
Interpretation: "Cover the main domain well, less others"
Next step: Generate posts for key verticals
```

### Multi-Industry Platform
```
Real posts: Mixed industries
Benchmark suite: Multi-industry
Expected pass rate: 70-90%
Interpretation: "Broad coverage working"
Next step: Fine-tune underperforming cases
```

### Pre-Launch Platform
```
Real posts: Sample/test posts
Benchmark suite: Industry standards
Expected pass rate: 40-60%
Interpretation: "Normal for development stage"
Next step: Iterate on generation quality
```

---

## GitHub CI Results

### If It Passes (80%+)
```
✅ Generation Quality Suite
   Pass rate: 85%
   Avg score: 92%
   
GitHub shows: GREEN checkmark
Meaning: Quality is solid
```

### If It Fails (< 80%)
```
❌ Generation Quality Suite
   Pass rate: 48%
   Avg score: 76%
   
GitHub shows: RED X
Meaning: Shows what needs improvement
Artifact: View details in generation_quality_report.ci.json
```

**Important**: Failing is GOOD info! It shows exactly which cases need work.

---

## Common Issues & Fixes

### Issue: "No posts found to export"
```
Fix: Generate posts in the app first
  - Go to http://localhost:5000
  - Create 5-10 posts
  - Posts auto-save to data/posts.json
```

### Issue: "Mapped 0 posts to benchmark cases"
```
Fix: Posts don't match case keywords
  - Update expectations in generation_quality_suite.sample.json
  - OR generate posts with more specific keywords
  - OR adjust must_include terms to match your style
```

### Issue: "CI workflow not running"
```
Fix: Check if file was actually committed
  - git status  # Verify file is staged
  - git push    # Must reach main branch
  - GitHub Actions tab should show run after 30 seconds
```

---

## Files Created/Modified

```
Created:
├─ benchmarks/export_real_generations.py
├─ benchmarks/results/latest_generation_outputs.json
├─ benchmarks/EXPORT_GUIDE.md
├─ benchmarks/REAL_DATA_ANALYSIS.md
└─ benchmarks/QUICK_REFERENCE.md (this file)

Modified:
├─ .github/workflows/generation_quality_ci.yml (increased gate to 80%)
└─ benchmarks/generation_quality_suite.sample.json (31 cases)
```

---

## One-Time Setup

Already done for you ✅

- Export script created
- CI workflow configured
- Benchmark suite built (31 cases)
- Local test validated (100% pass with samples)

You just need to:
1. Generate posts in your app
2. Run export script
3. Push to GitHub

---

## Timeline

```
NOW:
  ✅ Code ready to push
  ✅ Export script ready
  ✅ CI configured

WHEN YOU'RE READY (Day 1-3):
  1. Generate 5-10 posts (different industries)
  2. Run: python benchmarks/export_real_generations.py
  3. Run: python benchmarks/run_generation_quality_bench.py
  4. Review: Local results
  5. Push: git push origin main
  
IMMEDIATELY AFTER PUSH:
  ✅ GitHub CI runs automatically
  ✅ Report generated
  ✅ You can see results in Actions tab

DAILY (Optional):
  Generate more posts → Export → Push → CI validates
```

---

## Get Help

Check these files:
- `benchmarks/EXPORT_GUIDE.md` - Detailed export options
- `benchmarks/REAL_DATA_ANALYSIS.md` - Interpreting results
- `benchmarks/BENCHMARK_GUIDE.md` - Full benchmark documentation
