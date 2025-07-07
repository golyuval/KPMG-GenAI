#!/usr/bin/env python3
"""
Test to verify that unrelated queries get low similarity scores
"""

from rag import rag

def test_low_similarity_scores():
    print('🎯 Testing Low Similarity Scores for Unrelated Queries')
    print('=' * 60)
    
    # Test queries that should get LOW scores (unrelated to health services)
    unrelated_queries = [
        "How to fix a car engine",
        "Best pizza recipe in Italy", 
        "Python programming tutorial",
        "Stock market analysis",
        "Weather forecast for tomorrow",
        "Mathematics calculus integration",
        "Football match results",
        "Movie recommendations"
    ]
    
    # Test queries that should get MEDIUM scores (partially related)
    partially_related_queries = [
        "Doctor appointment",  # Related to health but not specific
        "Medical insurance",   # Related but generic
        "Health clinic",       # Related but vague
        "Hospital services"    # Related but not HMO-specific
    ]
    
    # Test queries that should get HIGH scores (highly related)
    highly_related_queries = [
        "דיקור סיני",          # Acupuncture - specific service
        "סדנת בריאות",         # Health workshop - exact match
        "מרפאות שיניים",       # Dental clinics - specific service
        "הריון ובדיקות",       # Pregnancy and tests - specific
        "מכבי זהב הטבות"       # Maccabi Gold benefits - exact match
    ]
    
    print('\n🔴 UNRELATED QUERIES (Expected: LOW scores < 0.3)')
    print('-' * 50)
    
    for query in unrelated_queries:
        result = rag.search(query, k=2)
        avg_score = result["metadata"]["avg_similarity_score"]
        top_score = result["metadata"]["top_score"]
        
        print(f'Query: "{query}"')
        print(f'   Avg Score: {avg_score:.3f} | Top Score: {top_score:.3f}')
        
        if avg_score < 0.3:
            print(f'   ✅ GOOD: Low score as expected')
        else:
            print(f'   ⚠️  ISSUE: Score too high for unrelated query')
        print()
    
    print('\n🟡 PARTIALLY RELATED QUERIES (Expected: MEDIUM scores 0.3-0.7)')
    print('-' * 50)
    
    for query in partially_related_queries:
        result = rag.search(query, k=2)
        avg_score = result["metadata"]["avg_similarity_score"]
        top_score = result["metadata"]["top_score"]
        
        print(f'Query: "{query}"')
        print(f'   Avg Score: {avg_score:.3f} | Top Score: {top_score:.3f}')
        
        if 0.3 <= avg_score <= 0.7:
            print(f'   ✅ GOOD: Medium score as expected')
        elif avg_score < 0.3:
            print(f'   ⚠️  ISSUE: Score too low for partially related query')
        else:
            print(f'   ✅ GOOD: High score (better than expected)')
        print()
    
    print('\n🟢 HIGHLY RELATED QUERIES (Expected: HIGH scores > 0.7)')
    print('-' * 50)
    
    for query in highly_related_queries:
        result = rag.search(query, k=2)
        avg_score = result["metadata"]["avg_similarity_score"]
        top_score = result["metadata"]["top_score"]
        
        print(f'Query: "{query}"')
        print(f'   Avg Score: {avg_score:.3f} | Top Score: {top_score:.3f}')
        
        if avg_score > 0.7:
            print(f'   ✅ GOOD: High score as expected')
        else:
            print(f'   ⚠️  ISSUE: Score too low for highly related query')
        print()
    
    print('\n' + '=' * 60)
    print('📊 SUMMARY')
    print('=' * 60)
    
    # Test a few more extreme cases
    print('\n🧪 EXTREME CASES:')
    
    # Test with complete nonsense
    nonsense_result = rag.search("xyzabc qwerty asdfgh", k=2)
    print(f'Nonsense query: {nonsense_result["metadata"]["avg_similarity_score"]:.3f}')
    
    # Test with empty/minimal query
    minimal_result = rag.search("a", k=2)
    print(f'Single character: {minimal_result["metadata"]["avg_similarity_score"]:.3f}')
    
    # Test with exact Hebrew medical terms
    exact_result = rag.search("קופת חולים מכבי", k=2)
    print(f'Exact HMO name: {exact_result["metadata"]["avg_similarity_score"]:.3f}')
    
    print('\n✅ Testing complete! Review scores above to verify similarity ranges.')

if __name__ == "__main__":
    test_low_similarity_scores() 