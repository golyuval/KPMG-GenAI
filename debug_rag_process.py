#!/usr/bin/env python3
"""
Debug script to show exactly how the RAG mechanism processes HTML files
This will break down each step and show what happens to the data
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json
import sys

# Create a file handler for output
output_file = open('rag_debug_output.txt', 'w', encoding='utf-8')

def print_to_file(*args, **kwargs):
    """Custom print function that writes to file instead of console"""
    print(*args, file=output_file, **kwargs)
    output_file.flush()  # Ensure immediate write

def debug_html_parsing():
    """
    Step 1: Show how HTML files are parsed and divided
    """
    print_to_file("="*80)
    print_to_file("STEP 1: HTML FILE PARSING AND DIVISION")
    print_to_file("="*80)
    
    data_path = Path("./Data/phase2_data")
    
    # Check if data directory exists
    if not data_path.exists():
        print_to_file(f"❌ Data directory not found: {data_path}")
        print_to_file("Available directories:")
        for p in Path(".").glob("**/Data"):
            print_to_file(f"  - {p}")
        return []
    
    all_processed_sections = []
    
    for file in data_path.glob("*.html"):
        print_to_file(f"\n📄 Processing file: {file.name}")
        print_to_file(f"   File size: {file.stat().st_size} bytes")
        
        try:
            hmo = file.stem
            print_to_file(f"   HMO extracted from filename: '{hmo}'")
            
            # Read HTML content
            with open(file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            print_to_file(f"   Raw HTML length: {len(html_content)} characters")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, "lxml")
            print_to_file(f"   Parsed with BeautifulSoup successfully")
            
            # Show original structure
            print_to_file(f"   HTML structure:")
            for tag in ['title', 'h1', 'h2', 'h3', 'h4', 'p']:
                elements = soup.find_all(tag)
                if elements:
                    print_to_file(f"     - {tag}: {len(elements)} elements")
            
            sections = []
            
            # Remove script and style elements
            scripts_removed = 0
            for script in soup(["script", "style"]):
                script.decompose()
                scripts_removed += 1
            
            if scripts_removed > 0:
                print_to_file(f"   🧹 Removed {scripts_removed} script/style elements")
            
            # Process headers and their content
            headers_found = 0
            for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                headers_found += 1
                section_title = header.get_text(strip=True)
                content = []
                
                # Get content following this header
                for sibling in header.find_next_siblings():
                    if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                        break
                    text = sibling.get_text(strip=True)
                    if text:
                        content.append(text)
                
                if content:
                    section_text = f"[כותרת: {section_title}] {' '.join(content)}"
                    full_section = f"[קופת חולים: {hmo}] {section_text}"
                    sections.append(full_section)
                    
                    print_to_file(f"   📝 Section created from header '{section_title}':")
                    print_to_file(f"      - Header: {section_title}")
                    print_to_file(f"      - Content parts: {len(content)}")
                    print_to_file(f"      - Total section length: {len(full_section)} chars")
                    print_to_file(f"      - Preview: {full_section[:100]}...")
            
            # If no headers found, process paragraphs
            if not sections:
                print_to_file(f"   ⚠️  No headers found, processing paragraphs...")
                paragraphs_processed = 0
                for p in soup.find_all('p'):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        full_section = f"[קופת חולים: {hmo}] {text}"
                        sections.append(full_section)
                        paragraphs_processed += 1
                        
                        print_to_file(f"   📝 Paragraph section {paragraphs_processed}:")
                        print_to_file(f"      - Length: {len(text)} chars")
                        print_to_file(f"      - Preview: {text[:100]}...")
                
                if paragraphs_processed == 0:
                    print_to_file(f"   ⚠️  No paragraphs found, extracting all text...")
                    text = soup.get_text(separator=' ', strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    if text:
                        full_section = f"[קופת חולים: {hmo}] {text}"
                        sections.append(full_section)
                        print_to_file(f"   📝 Full text section:")
                        print_to_file(f"      - Length: {len(text)} chars")
                        print_to_file(f"      - Preview: {text[:100]}...")
            
            print_to_file(f"   ✅ Total sections created: {len(sections)}")
            all_processed_sections.extend(sections)
            
            # Show first section in detail
            if sections:
                print_to_file(f"\n   🔍 DETAILED VIEW OF FIRST SECTION:")
                print_to_file(f"   {'-'*50}")
                print_to_file(f"   {sections[0]}")
                print_to_file(f"   {'-'*50}")
            
        except Exception as e:
            print_to_file(f"   ❌ Error processing {file}: {str(e)}")
            continue
    
    print_to_file(f"\n📊 SUMMARY:")
    print_to_file(f"   - Total sections across all files: {len(all_processed_sections)}")
    
    return all_processed_sections

def debug_text_splitting(sections):
    """
    Step 2: Show how text is split into chunks
    """
    print_to_file("\n" + "="*80)
    print_to_file("STEP 2: TEXT SPLITTING INTO CHUNKS")
    print_to_file("="*80)
    
    # Create the same splitter as in the original code
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        length_function=len,
    )
    
    print_to_file(f"📏 Text Splitter Configuration:")
    print_to_file(f"   - Chunk size: {splitter._chunk_size}")
    print_to_file(f"   - Chunk overlap: {splitter._chunk_overlap}")
    print_to_file(f"   - Separators: {splitter._separators}")
    
    all_chunks = []
    
    for i, section in enumerate(sections[:3]):  # Show first 3 sections for detail
        print_to_file(f"\n🔄 Processing section {i+1}:")
        print_to_file(f"   Original length: {len(section)} characters")
        print_to_file(f"   Preview: {section[:100]}...")
        
        # Extract HMO name
        hmo_match = re.search(r'\[קופת חולים: ([^\]]+)\]', section)
        hmo_name = hmo_match.group(1) if hmo_match else "unknown"
        print_to_file(f"   HMO extracted: '{hmo_name}'")
        
        # Split into chunks
        chunks = splitter.split_text(section)
        print_to_file(f"   🔪 Split into {len(chunks)} chunks:")
        
        for j, chunk in enumerate(chunks):
            print_to_file(f"      Chunk {j+1}:")
            print_to_file(f"        - Length: {len(chunk)} characters")
            print_to_file(f"        - Preview: {chunk[:80]}...")
            if len(chunk) > 80:
                print_to_file(f"        - End: ...{chunk[-40:]}")
            
            all_chunks.append({
                'content': chunk,
                'hmo': hmo_name,
                'chunk_index': j,
                'section_index': i,
                'length': len(chunk)
            })
    
    # Show statistics for all sections
    if len(sections) > 3:
        print_to_file(f"\n📊 Processing remaining {len(sections)-3} sections...")
        for i, section in enumerate(sections[3:], 3):
            hmo_match = re.search(r'\[קופת חולים: ([^\]]+)\]', section)
            hmo_name = hmo_match.group(1) if hmo_match else "unknown"
            chunks = splitter.split_text(section)
            
            for j, chunk in enumerate(chunks):
                all_chunks.append({
                    'content': chunk,
                    'hmo': hmo_name,
                    'chunk_index': j,
                    'section_index': i,
                    'length': len(chunk)
                })
    
    print_to_file(f"\n📊 CHUNKING SUMMARY:")
    print_to_file(f"   - Total chunks created: {len(all_chunks)}")
    print_to_file(f"   - Average chunk length: {sum(c['length'] for c in all_chunks) / len(all_chunks):.0f} chars")
    print_to_file(f"   - Chunks by HMO:")
    
    hmo_counts = {}
    for chunk in all_chunks:
        hmo = chunk['hmo']
        hmo_counts[hmo] = hmo_counts.get(hmo, 0) + 1
    
    for hmo, count in hmo_counts.items():
        print_to_file(f"     - {hmo}: {count} chunks")
    
    return all_chunks

def debug_document_creation(chunks):
    """
    Step 3: Show how chunks are converted to Document objects
    """
    print_to_file("\n" + "="*80)
    print_to_file("STEP 3: DOCUMENT CREATION WITH METADATA")
    print_to_file("="*80)
    
    documents = []
    
    print_to_file(f"📋 Creating Document objects from {len(chunks)} chunks...")
    
    for i, chunk_data in enumerate(chunks[:5]):  # Show first 5 in detail
        doc = Document(
            page_content=chunk_data['content'],
            metadata={
                "hmo": chunk_data['hmo'],
                "chunk_index": chunk_data['chunk_index'],
                "source": f"{chunk_data['hmo']}_chunk_{chunk_data['chunk_index']}",
                "timestamp": datetime.now().isoformat()
            }
        )
        documents.append(doc)
        
        print_to_file(f"\n📄 Document {i+1}:")
        print_to_file(f"   Page content length: {len(doc.page_content)} chars")
        print_to_file(f"   Metadata: {json.dumps(doc.metadata, indent=6, ensure_ascii=False)}")
        print_to_file(f"   Content preview: {doc.page_content[:100]}...")
    
    # Create remaining documents
    for chunk_data in chunks[5:]:
        doc = Document(
            page_content=chunk_data['content'],
            metadata={
                "hmo": chunk_data['hmo'],
                "chunk_index": chunk_data['chunk_index'],
                "source": f"{chunk_data['hmo']}_chunk_{chunk_data['chunk_index']}",
                "timestamp": datetime.now().isoformat()
            }
        )
        documents.append(doc)
    
    print_to_file(f"\n📊 DOCUMENT CREATION SUMMARY:")
    print_to_file(f"   - Total documents created: {len(documents)}")
    print_to_file(f"   - Document types: All are langchain.schema.Document objects")
    print_to_file(f"   - Metadata fields: hmo, chunk_index, source, timestamp")
    
    # Show metadata distribution
    hmo_doc_counts = {}
    for doc in documents:
        hmo = doc.metadata['hmo']
        hmo_doc_counts[hmo] = hmo_doc_counts.get(hmo, 0) + 1
    
    print_to_file(f"   - Documents by HMO:")
    for hmo, count in hmo_doc_counts.items():
        print_to_file(f"     - {hmo}: {count} documents")
    
    return documents

def debug_vector_storage_simulation(documents):
    """
    Step 4: Show how documents would be stored in vector database
    """
    print_to_file("\n" + "="*80)
    print_to_file("STEP 4: VECTOR STORAGE SIMULATION")
    print_to_file("="*80)
    
    print_to_file(f"🔢 Vector Storage Process:")
    print_to_file(f"   - Input: {len(documents)} Document objects")
    print_to_file(f"   - Each document will be converted to embeddings using Azure OpenAI")
    print_to_file(f"   - Embeddings will be stored in FAISS vector database")
    print_to_file(f"   - FAISS uses COSINE distance with L2 normalization")
    
    print_to_file(f"\n📊 Storage Structure Preview:")
    
    for i, doc in enumerate(documents[:3]):
        print_to_file(f"\n   Document {i+1} → Vector {i+1}:")
        print_to_file(f"      Original text: {doc.page_content[:60]}...")
        print_to_file(f"      Metadata: {doc.metadata}")
        print_to_file(f"      → Will become: 1536-dimensional embedding vector")
        print_to_file(f"      → Stored with metadata for retrieval")
    
    if len(documents) > 3:
        print_to_file(f"\n   ... and {len(documents)-3} more documents")
    
    print_to_file(f"\n🔍 How Search Works:")
    print_to_file(f"   1. Query text is converted to embedding vector")
    print_to_file(f"   2. FAISS finds most similar vectors using cosine similarity")
    print_to_file(f"   3. Similar vectors are converted back to original text")
    print_to_file(f"   4. Metadata is used to provide context (HMO, chunk info)")
    
    return len(documents)

def main():
    """
    Main function to run the complete debugging process
    """
    print_to_file("🚀 Starting RAG Mechanism Debug Analysis")
    print_to_file("This will show exactly how HTML files are processed and stored")
    
    # Step 1: Parse HTML files
    sections = debug_html_parsing()
    
    if not sections:
        print_to_file("\n❌ No sections were processed. Check your data directory.")
        return
    
    # Step 2: Split text into chunks
    chunks = debug_text_splitting(sections)
    
    # Step 3: Create Document objects
    documents = debug_document_creation(chunks)
    
    # Step 4: Simulate vector storage
    vector_count = debug_vector_storage_simulation(documents)
    
    print_to_file("\n" + "="*80)
    print_to_file("🎯 COMPLETE PROCESS SUMMARY")
    print_to_file("="*80)
    print_to_file(f"HTML Files → Sections → Chunks → Documents → Vectors")
    print_to_file(f"           → {len(sections)} sections")
    print_to_file(f"                    → {len(chunks)} chunks")
    print_to_file(f"                             → {len(documents)} documents")
    print_to_file(f"                                      → {vector_count} vectors")
    
    print_to_file(f"\n✅ Debug analysis complete!")
    print_to_file(f"Now you can see exactly how your RAG mechanism processes data.")
    
    # Close the output file
    output_file.close()
    print(f"✅ Debug analysis complete! Output saved to 'rag_debug_output.txt'")

if __name__ == "__main__":
    main() 