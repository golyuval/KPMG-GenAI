#!/usr/bin/env python3
"""
Test to verify similarity scoring fix is working
"""

from rag import rag

def test_similarity_fix():
    print('🔧 Testing Similarity Scoring Fix')
    print('=' * 50)
    
    # Test similarity function directly
    print('📊 Testing Similarity Function:')
    test_distances = [0.0, 0.5, 1.0, 1.5, 2.0]
    
    for distance in test_distances:
        similarity = rag.similarity(distance)
        print(f'   Distance: {distance:.1f} → Similarity: {similarity:.3f}')
    
    print('\n✅ Expected: Distance 0.0 = 1.0, Distance 2.0 = 0.0')
    
    # Test real search
    print('\n🔍 Testing Real Search with Fixed Scoring:')
    
    result = rag.search('דיקור סיני', k=3)
    
    print(f'   Results found: {len(result["documents"])}')
    print(f'   Avg similarity score: {result["metadata"]["avg_similarity_score"]:.3f}')
    print(f'   Top score: {result["metadata"]["top_score"]:.3f}')
    print(f'   Response time: {result["metadata"]["retrieval_time_ms"]:.1f}ms')
    
    # Show individual scores
    print('\n📋 Individual Result Scores:')
    for i, score in enumerate(result["scores"]):
        print(f'   Result {i+1}: {score:.3f}')
    
    # Test another query
    print('\n🎯 Testing Another Query:')
    result2 = rag.search('מחיר משקפיים', k=3)
    
    print(f'   Avg similarity score: {result2["metadata"]["avg_similarity_score"]:.3f}')
    print(f'   Top score: {result2["metadata"]["top_score"]:.3f}')
    
    # Show individual scores
    print('\n📋 Individual Result Scores:')
    for i, score in enumerate(result2["scores"]):
        print(f'   Result {i+1}: {score:.3f}')
    
    print('\n' + '=' * 50)
    if all(score != 0.5 for score in result["scores"] + result2["scores"]):
        print('✅ SUCCESS: Similarity scoring is now working correctly!')
        print('   No more fixed 0.5 scores - scores are now variable!')
    else:
        print('❌ ISSUE: Still getting some 0.5 scores')
        print('   This means the fix may not be fully working')
    
    print('=' * 50)

if __name__ == "__main__":
    test_similarity_fix() 