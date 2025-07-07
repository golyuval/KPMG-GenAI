#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag import rag
import numpy as np

def debug_raw_similarities():
    """Debug the raw FAISS similarity calculations"""
    
    print("DEBUGGING RAW SIMILARITY CALCULATIONS")
    print("=" * 60)
    
    # Test queries
    queries = [
        "הריון",  # Should be highly relevant
        "בדיקות הריון",  # Should be highly relevant
        "מכונאות רכב ומשאיות",  # Should be irrelevant
        "nfubtu, rfc",  # Should be irrelevant gibberish
        "שירותי בריאות",  # Should be somewhat relevant
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        # Get raw FAISS results (without enhancement)
        try:
            raw_results = rag.vstore.similarity_search_with_score(query, k=5)
            
            print(f"Raw FAISS results ({len(raw_results)} found):")
            
            for i, (doc, raw_distance) in enumerate(raw_results):
                # Convert distance to similarity using current method
                similarity = rag.similarity(raw_distance)
                
                # Get content preview
                content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                
                print(f"  [{i+1}] Raw distance: {raw_distance:.4f} -> Similarity: {similarity:.4f}")
                print(f"      Content: {content_preview}")
                print(f"      HMO: {doc.metadata.get('hmo', 'unknown')}")
                print()
            
            # Calculate statistics
            distances = [raw_distance for _, raw_distance in raw_results]
            similarities = [rag.similarity(d) for d in distances]
            
            print(f"Statistics:")
            print(f"  Raw distances - Min: {min(distances):.4f}, Max: {max(distances):.4f}, Avg: {np.mean(distances):.4f}")
            print(f"  Similarities - Min: {min(similarities):.4f}, Max: {max(similarities):.4f}, Avg: {np.mean(similarities):.4f}")
            
            # Check if the problem is in embedding quality
            if query in ["מכונאות רכב ומשאיות", "nfubtu, rfc"]:
                if max(similarities) > 0.5:
                    print(f"  ⚠️  WARNING: Unrelated query '{query}' has high similarity ({max(similarities):.4f})")
                    print(f"      This suggests the embeddings are not discriminating well")
                    
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "=" * 60)
    print("EMBEDDING ANALYSIS")
    print("=" * 60)
    
    # Test embedding generation directly
    try:
        # Generate embeddings for related and unrelated queries
        related_query = "הריון"
        unrelated_query = "מכונאות רכב"
        
        related_embedding = rag.embeddings.embed_query(related_query)
        unrelated_embedding = rag.embeddings.embed_query(unrelated_query)
        
        print(f"Embedding dimensions: {len(related_embedding)}")
        print(f"Related query embedding norm: {np.linalg.norm(related_embedding):.4f}")
        print(f"Unrelated query embedding norm: {np.linalg.norm(unrelated_embedding):.4f}")
        
        # Calculate cosine similarity directly
        dot_product = np.dot(related_embedding, unrelated_embedding)
        cosine_sim = dot_product / (np.linalg.norm(related_embedding) * np.linalg.norm(unrelated_embedding))
        
        print(f"Direct cosine similarity between '{related_query}' and '{unrelated_query}': {cosine_sim:.4f}")
        
        if cosine_sim > 0.3:
            print("  ⚠️  WARNING: High cosine similarity between unrelated concepts")
            print("      This indicates the embedding model is not domain-specific enough")
        
    except Exception as e:
        print(f"Embedding analysis error: {e}")

def analyze_document_embeddings():
    """Analyze the document embeddings in the vector store"""
    
    print("\n" + "=" * 60)
    print("DOCUMENT EMBEDDING ANALYSIS")
    print("=" * 60)
    
    # Get some sample documents
    try:
        # Search for pregnancy-related content
        pregnancy_results = rag.vstore.similarity_search_with_score("הריון", k=3)
        
        print("Sample pregnancy-related documents:")
        for i, (doc, distance) in enumerate(pregnancy_results):
            print(f"  [{i+1}] Distance: {distance:.4f}, Content: {doc.page_content[:80]}...")
        
        # Search for car-related content (should be low similarity)
        car_results = rag.vstore.similarity_search_with_score("מכונאות רכב", k=3)
        
        print("\nSample results for car mechanics query:")
        for i, (doc, distance) in enumerate(car_results):
            print(f"  [{i+1}] Distance: {distance:.4f}, Content: {doc.page_content[:80]}...")
        
        # Compare the distances
        pregnancy_distances = [d for _, d in pregnancy_results]
        car_distances = [d for _, d in car_results]
        
        print(f"\nDistance comparison:")
        print(f"  Pregnancy query avg distance: {np.mean(pregnancy_distances):.4f}")
        print(f"  Car query avg distance: {np.mean(car_distances):.4f}")
        print(f"  Difference: {np.mean(car_distances) - np.mean(pregnancy_distances):.4f}")
        
        if np.mean(car_distances) - np.mean(pregnancy_distances) < 0.2:
            print("  ⚠️  WARNING: Small difference in distances between related and unrelated queries")
            print("      This suggests poor semantic discrimination in the vector space")
            
    except Exception as e:
        print(f"Document analysis error: {e}")

if __name__ == "__main__":
    debug_raw_similarities()
    analyze_document_embeddings() 