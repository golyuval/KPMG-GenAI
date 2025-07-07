#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Starting simple test...")

try:
    from rag import rag
    print("✓ RAG imported successfully")
    
    print(f"✓ Vector store has {rag.vstore.index.ntotal} vectors")
    
    # Test basic search
    print("\n--- Testing basic search ---")
    
    # Test with pregnancy query
    pregnancy_results = rag.vstore.similarity_search_with_score("הריון", k=3)
    print(f"Pregnancy query returned {len(pregnancy_results)} results")
    
    for i, (doc, distance) in enumerate(pregnancy_results):
        similarity = rag.similarity(distance)
        print(f"  [{i+1}] Distance: {distance:.4f} -> Similarity: {similarity:.4f}")
        print(f"      Content: {doc.page_content[:50]}...")
    
    # Test with car query
    print("\n--- Testing car query ---")
    car_results = rag.vstore.similarity_search_with_score("מכונאות רכב", k=3)
    print(f"Car query returned {len(car_results)} results")
    
    for i, (doc, distance) in enumerate(car_results):
        similarity = rag.similarity(distance)
        print(f"  [{i+1}] Distance: {distance:.4f} -> Similarity: {similarity:.4f}")
        print(f"      Content: {doc.page_content[:50]}...")
    
    print("\n--- Analysis ---")
    pregnancy_distances = [d for _, d in pregnancy_results]
    car_distances = [d for _, d in car_results]
    
    print(f"Pregnancy avg distance: {sum(pregnancy_distances)/len(pregnancy_distances):.4f}")
    print(f"Car avg distance: {sum(car_distances)/len(car_distances):.4f}")
    print(f"Difference: {sum(car_distances)/len(car_distances) - sum(pregnancy_distances)/len(pregnancy_distances):.4f}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 