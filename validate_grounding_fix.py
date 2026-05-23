#!/usr/bin/env python3
"""
Quick validation of the grounding contract fix.
Run this to verify the changes are working correctly.
"""

def validate_grounding_fix():
    """
    Validate the grounding contract thresholds and hybrid scoring math.
    """
    print("\n" + "="*70)
    print("GROUNDING CONTRACT FIX - VALIDATION")
    print("="*70 + "\n")
    
    # Scenario 1: Before fix (problematic case)
    print("SCENARIO 1: Before Fix (match_threshold=0.50, strict/balanced weights)")
    print("-" * 70)
    
    vector_sim_before = 0.50
    keyword_sim_before = 0.0  # No keyword match
    vector_weight = 0.75
    keyword_weight = 0.25
    
    hybrid_score_before = vector_weight * vector_sim_before + keyword_weight * keyword_sim_before
    
    print(f"  Vector match: {vector_sim_before:.2f}")
    print(f"  Keyword match: {keyword_sim_before:.2f}")
    print(f"  Hybrid score = 0.75 × {vector_sim_before:.2f} + 0.25 × {keyword_sim_before:.2f}")
    print(f"  Hybrid score = {hybrid_score_before:.4f}")
    print()
    print(f"  Grounding contract (old):")
    print(f"    Balanced: needs >= 0.42, got {hybrid_score_before:.4f} → {'✅ PASS' if hybrid_score_before >= 0.42 else '❌ FAIL'}")
    print(f"    Strict:   needs >= 0.56, got {hybrid_score_before:.4f} → {'✅ PASS' if hybrid_score_before >= 0.56 else '❌ FAIL'}")
    print()
    
    # Scenario 2: After fix (with keywords)
    print("SCENARIO 2: After Fix (match_threshold=0.30 + keyword boost)")
    print("-" * 70)
    
    test_cases = [
        ("No keyword match", 0.30, 0.0),
        ("Partial keyword match", 0.30, 0.5),
        ("Full keyword match", 0.30, 1.0),
        ("Mid-range match", 0.40, 0.7),
        ("Good match", 0.50, 0.8),
    ]
    
    for label, vector, keyword in test_cases:
        hybrid = vector_weight * vector + keyword_weight * keyword
        
        balanced_ok = hybrid >= 0.35
        strict_ok = hybrid >= 0.45
        
        print(f"\n  {label}:")
        print(f"    Vector: {vector:.2f}, Keyword: {keyword:.2f}")
        print(f"    Hybrid = 0.75 × {vector:.2f} + 0.25 × {keyword:.2f} = {hybrid:.4f}")
        print(f"    Balanced (need 0.35): {'✅ PASS' if balanced_ok else '❌ FAIL'}")
        print(f"    Strict (need 0.45):   {'✅ PASS' if strict_ok else '❌ FAIL'}")
    
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70 + "\n")
    
    # Check current app.py values
    print("Checking app.py configuration...")
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Check for new thresholds
        has_030 = 'match_threshold=0.30' in content
        has_k8 = 'k=8' in content and 'retrieval' in content.lower()
        has_045 = 'min_avg_similarity = 0.45' in content
        has_035 = '0.35 if grounding_mode' in content
        
        print(f"  ✓ match_threshold=0.30: {'✅' if has_030 else '❌'}")
        print(f"  ✓ k=8 (retrieval count): {'✅' if has_k8 else '❌'}")
        print(f"  ✓ strict threshold=0.45: {'✅' if has_045 else '❌'}")
        print(f"  ✓ balanced threshold=0.35: {'✅' if has_035 else '❌'}")
        print()
        
        if has_030 and has_k8 and has_045 and has_035:
            print("✅ All changes successfully applied!")
        else:
            print("⚠️  Some changes may not be applied correctly")
            
    except Exception as e:
        print(f"⚠️  Could not verify app.py: {e}")
    
    print("\n" + "=" * 70)
    print("NEXT STEP: Test in dashboard")
    print("=" * 70 + "\n")
    print("1. Start the app: python app.py")
    print("2. Go to Create Post")
    print("3. Select 'Balanced' grounding mode")
    print("4. Generate a post")
    print("5. Should see ✅ grounding success (no error message)")
    print()


if __name__ == '__main__':
    validate_grounding_fix()
