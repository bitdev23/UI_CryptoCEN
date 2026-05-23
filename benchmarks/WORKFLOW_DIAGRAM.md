# Export & Push Workflow

## Complete Workflow Visualization

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     YOU: LOCAL MACHINE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Step 1: Export Real Posts                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ $ python benchmarks/export_real_generations.py --limit 31       │   │
│  │                                                                   │   │
│  │ Reads:  data/posts.json (41 posts you've generated)             │   │
│  │ Exports: benchmarks/results/latest_generation_outputs.json      │   │
│  │          ├─ post_0: "Blockchain transaction finality..."        │   │
│  │          ├─ post_1: "Proof of Stake finality..."                │   │
│  │          └─ post_30: "..."                                       │   │
│  │                                                                   │   │
│  │ ✅ Output: 31 posts ready for testing                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Step 2: Test Locally (Optional)                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ $ python benchmarks/run_generation_quality_bench.py \           │   │
│  │     --responses latest_generation_outputs.json                  │   │
│  │                                                                   │   │
│  │ Compares: Real posts vs 31 benchmark cases                      │   │
│  │ Scores:   0% pass rate (posts don't match cases)                │   │
│  │ Report:   benchmarks/results/generation_quality_report.*.json   │   │
│  │                                                                   │   │
│  │ ✅ Output: Know your quality score BEFORE pushing               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Step 3: Commit & Push                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ $ git add benchmarks/results/latest_generation_outputs.json     │   │
│  │ $ git commit -m "Add real generation outputs for CI validation" │   │
│  │ $ git push origin main                                           │   │
│  │                                                                   │   │
│  │ ✅ Output: Code on GitHub main branch                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Push detected
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                   GITHUB: AUTOMATIC CI RUNS                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Workflow Trigger                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Event: benchmarks/*.json file changed                            │   │
│  │ Trigger: GitHub Actions (.github/workflows/*.yml)               │   │
│  │ Time: Automatic, ~30 seconds after push                         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  CI Steps (Automatic)                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 1. Checkout code                                                 │   │
│  │ 2. Install Python 3.10                                          │   │
│  │ 3. Run:                                                          │   │
│  │    python benchmarks/run_generation_quality_bench.py \          │   │
│  │      --suite generation_quality_suite.sample.json \             │   │
│  │      --responses latest_generation_outputs.json \               │   │
│  │      --min-pass-rate 80                                         │   │
│  │ 4. Generate report                                              │   │
│  │ 5. Upload artifact: generation-quality-report                   │   │
│  │                                                                   │   │
│  │ Status: ✅ Passed OR ❌ Failed (based on pass_rate >= 80%)       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ CI completes
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      YOU: GITHUB WEB INTERFACE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  View Results                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Go to: github.com/YOUR_ORG/UI_CryptoCEN/actions                 │   │
│  │                                                                   │   │
│  │ See: Generation Quality Suite workflow run                      │   │
│  │                                                                   │   │
│  │ Status: ✅ All checks passed (if pass_rate >= 80%)             │   │
│  │    OR   ❌ Checks failed (if pass_rate < 80%)                  │   │
│  │                                                                   │   │
│  │ Download: Artifact (generation-quality-report.ci.json)          │   │
│  │                                                                   │   │
│  │ Content: {                                                       │   │
│  │   "summary": {                                                   │   │
│  │     "total_cases": 31,                                           │   │
│  │     "passed_cases": 28,                                          │   │
│  │     "pass_rate": 90.3%,                                          │   │
│  │     "avg_score": 87.5%                                           │   │
│  │   },                                                              │   │
│  │   "results": [...]                                              │   │
│  │ }                                                                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Interpret Results                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ ✅ If pass_rate >= 80%:                                         │   │
│  │    "Your posts meet quality expectations"                       │   │
│  │                                                                   │   │
│  │ ⚠️  If 70-80%:                                                  │   │
│  │    "Good, but room for improvement"                             │   │
│  │                                                                   │   │
│  │ ❌ If < 70%:                                                    │   │
│  │    "Posts need tuning"                                          │   │
│  │    → Check which cases failed                                    │   │
│  │    → Adjust generation prompt                                    │   │
│  │    → Push changes → CI re-validates                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Real Example Timeline

### 10:00 AM - You
```bash
$ python benchmarks/export_real_generations.py --limit 31
✅ Exported 31 posts
```

### 10:01 AM - You
```bash
$ python benchmarks/run_generation_quality_bench.py \
  --responses benchmarks/results/latest_generation_outputs.json \
  --min-pass-rate 80
{
  "pass_rate": 48.4,
  "avg_score": 76.3
}
Benchmark failed: pass_rate=48.4 < min_pass_rate=80
```

**Decision:** Score is low but that's OK - shows real data vs expectations

### 10:05 AM - You
```bash
$ git add benchmarks/results/latest_generation_outputs.json
$ git commit -m "Add real generation outputs for CI validation"
$ git push origin main
```

### 10:07 AM - GitHub
```
✓ Repository received push
✓ Detected benchmark file change
✓ Started "Generation Quality Suite" workflow
```

### 10:09 AM - GitHub CI
```
✓ Checked out code
✓ Installed dependencies
✓ Ran benchmark against your posts
✓ Generated report
✓ Status: ❌ FAILED (pass_rate=48.4%)
✓ Uploaded artifact: generation-quality-report.ci.json
```

### 10:10 AM - You (Check Results)
```
GitHub Actions tab shows:
❌ Generation Quality Suite - FAILED

Details:
  - Pass rate: 48.4%
  - Avg score: 76.3%
  - Status: Below 80% gate

Artifact available: generation-quality-report.ci.json
```

**Interpretation:**
- Posts are valid but don't match multi-industry suite
- Crypto focus is strong (just not other industries)
- Options:
  1. Generate posts for other industries
  2. Adjust suite to crypto-only
  3. Keep as-is (shows coverage gap)

---

## Key Points

1. **Export** is LOCAL - no impact on production
2. **Test** locally before pushing (see score first)
3. **Push** triggers CI automatically (no manual setup needed)
4. **CI** runs in GitHub servers (isolated, read-only to code)
5. **Report** shows exactly what needs improvement
6. **Loop** can repeat as you improve generation

---

## You Don't Need To Do Anything Extra

✅ Export script - Created  
✅ CI workflow - Configured  
✅ Benchmark suite - Built (31 cases)  
✅ Local test - Passed (sample data 100%)  

Just:
1. Export posts when ready
2. Push to GitHub
3. CI does the rest automatically

**That's it!** No manual CI setup, no secrets to configure, no server changes needed.
