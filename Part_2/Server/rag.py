
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain.schema import Document
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List
import re
import logging
import time
import hashlib
from functools import lru_cache

from Core import config
from Core.logger_setup import get_logger 


# ------------- logger ----------------------------------------------

logger = get_logger(__name__)


class RAG:
    
    def __init__(self):

        self.embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=config.openai_endpoint,
            api_key=config.openai_key,
            deployment=config.openai_emb,
            api_version=config.openai_version,
        )

        self.vstore = self.build()
        self.search_count = 0
        self.search_history = []
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info(f"RAG initialized with {self.vstore.index.ntotal} vectors")

    # ------------- main RAG functionalities -------------------------------------------

    def build(self):
        
        # -------- splitter -----------------------------------------------

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
            length_function=len,
        )
        
        # -------- docs -----------------------------------------------

        docs = []

        for content in self.parse_html():
            
            # ------ HMO ------------------

            hmo_match = re.search(r'\[קופת חולים: ([^\]]+)\]', content)
            hmo_name = hmo_match.group(1) if hmo_match else "unknown"
            
            # ------ split to chunks ------------------
            
            chunks = splitter.split_text(content)
            
            # ------ create advanced docs ------------------
            
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "hmo": hmo_name,
                        "chunk_index": i,
                        "source": f"{hmo_name}_chunk_{i}",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                docs.append(doc)
        
        
        
        if docs:

            # total_tokens = 0
            # for doc in docs:
            #     # Rough estimation: ~1 token per 4 characters
            #     estimated_tokens = len(doc.page_content) / 4
            #     total_tokens += estimated_tokens
            
            # token_usage["text-embedding-ada-002"]["total_tokens"] += int(total_tokens)
            # token_usage["text-embedding-ada-002"]["total_cost"] += (total_tokens / 1000) * token_pricing["text-embedding-ada-002"]
            
            # logger.info(f"Embedding {len(docs)} documents, estimated {int(total_tokens)} tokens")
            
            # ------ Index built --------------------------------
            
            vstore = FAISS.from_documents(docs, self.embeddings)
            return vstore
        
        else:
            logger.error("No documents to index!")
            raise ValueError("No documents found to build vector store")

    def search(self, query: str, k: int = 4) -> Dict:
        
        start_time = time.time()
        
        # ------ cache check -----------------------
            
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_key = f"{query_hash}_{k}"
        
        if cache_key in self.cache:
            self.cache_hits += 1
            logger.info(f"Cache hit for query: {query[:50]}...")
            cached_result = self.cache[cache_key]
            cached_result["metadata"]["from_cache"] = True
            return cached_result
        
        self.cache_misses += 1
        
        # ------ similarity search ------------------
            
        try:
            results = self.vstore.similarity_search_with_score(query, k=k)
        
        except Exception as e:

            logger.error(f"Search error: {str(e)}")

            return {
                "documents": [],
                "scores": [],
                "metadata": {
                    "error": str(e),
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        logger.info(f"FAISS index built successfully with {self.vstore.index.ntotal} vectors")

        # ------ extract docs and scores -----------------------
        
        docs = []
        scores = []
        doc_metadata = []
        
        for doc, score in results:
            docs.append(doc.page_content)
            scores.append(float(score))
            doc_metadata.append(doc.metadata)
        
        # ------ prepare search record --------------------------
        
        avg_score = sum(scores) / len(scores) if scores else 0
        retrieval_time = time.time() - start_time
        
        search_record = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "num_results": len(docs),
            "avg_similarity_score": avg_score,
            "retrieval_time_ms": retrieval_time * 1000,
            "top_score": min(scores) if scores else None,  # FAISS uses L2 distance
            "from_cache": False,
            "results_preview": [
                {
                    "content": d[:200] + "..." if len(d) > 200 else d,
                    "score": s,
                    "metadata": m
                } 
                for d, s, m in zip(docs, scores, doc_metadata)
            ]
        }
        
        # ------ Bad match (no matching result) -----------------------
        
        if avg_score > 1.0:  # High L2 distance = poor match
            logger.warning(f"Poor retrieval quality for query: {query[:50]}... (avg distance: {avg_score:.3f})")
        

        result = {
            "documents": docs,
            "scores": scores,
            "metadata": search_record
        }

        # ------ updates -----------------------

        # tracking tokens
        self.search_history.append(search_record)
        self.search_count += 1
        
        # caching (max 1000)

        self.cache[cache_key] = result
        
        if len(self.cache) > 1000:
            oldest_keys = list(self.cache.keys())[:100]
            for key in oldest_keys:
                del self.cache[key]
        
        return result

    # ------------- helpers -------------------------------------------

    def parse_html(self):
        
        doc_count = 0
        
        for file in Path("./Data/phase2_data").glob("*.html"):
            try:
                hmo = file.stem
                
                with open(file, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), "lxml")
                
                sections = []

                # ------- Remove : script / style --------------------------------------

                for script in soup(["script", "style"]):
                    script.decompose()

                # ------- Divide : headers --------------------------------------

                for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                    
                    section_title = header.get_text(strip=True)
                    content = []
                    
                    for sibling in header.find_next_siblings():
                        if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                            break
                        text = sibling.get_text(strip=True)
                        if text:
                            content.append(text)
                    
                    if content:
                        section_text = f"[כותרת: {section_title}] {' '.join(content)}"
                        sections.append(f"[קופת חולים: {hmo}] {section_text}")
                
                # ------- Divide : paragraph (if no headers) ---------------------

                if not sections:
                    for p in soup.find_all('p'):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:  # Skip very short paragraphs
                            sections.append(f"[קופת חולים: {hmo}] {text}")
                
                # ------- Get all Text (no paragraphs) ----------------------------

                if not sections:
                    text = soup.get_text(separator=' ', strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    if text:
                        sections.append(f"[קופת חולים: {hmo}] {text}")
                
                doc_count += 1

                logger.info(f"Processed {hmo}: {len(sections)} sections")
                
                for section in sections:
                    yield section
                    
            except Exception as e:
                logger.error(f"Error processing {file}: {str(e)}")
                continue
        
        logger.info(f"Total documents processed: {doc_count}")

    def get_cache_stats(self) -> Dict:
        
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        # ---- avg retrieval time ----------------------------

        retrieval_times = [
            s["retrieval_time_ms"] 
            for s in self.search_history 
            if not s.get("from_cache", False)
        ]
        avg_retrieval_ms = sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0
        
        # ---- poor retrievals ----------------------------

        poor_quality_count = sum(
            1 for s in self.search_history 
            if s.get("avg_similarity_score", 0) > 1.0
        )
        
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "total_searches": self.search_count,
            "avg_retrieval_ms": avg_retrieval_ms,
            "poor_quality_count": poor_quality_count,
            "poor_quality_rate": poor_quality_count / self.search_count if self.search_count > 0 else 0
        }

# ------------- initialize rag --------------------------------------

rag = RAG()