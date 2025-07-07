from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain.schema import Document
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Tuple
import re
import time

import config
from Core.logger import get_logger 


# ------------- logger ----------------------------------------------

logger = get_logger(__name__)

RELEVANCE_THRESHOLD = 0.5   # ignore really weak docs
STRONG_THRESHOLD     = 0.8
MIDDLE_THRESHOLD     = 0.65

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

        logger.info(f"RAG initialized with {self.vstore.index.ntotal} vectors")

    # ------------- main RAG functionalities -------------------------------------------

    def build(self):
        
        # -------- splitter -----------------------------------------------

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,  # Increased for better context retention
            chunk_overlap=300,  # Increased overlap for better continuity
            separators=[
                "\n\n\n",  # Multiple paragraph breaks
                "\n\n",    # Paragraph breaks
                "\n",      # Line breaks
                ".",       # Sentences
                "!",       # Exclamations
                "?",       # Questions
                ";",       # Semicolons
                ":",       # Colons
                ",",       # Commas
                " ",       # Spaces
                ""         # Characters
            ],
            length_function=len,
            is_separator_regex=False,
        )
        
        # -------- docs -----------------------------------------------

        docs = []

        for content in self.parse_html():
            
            # ------ file name ------------------

            file_match = re.search(r'\[\*\*קובץ\*\*: ([^\]]+)\]', content)
            file_name = file_match.group(1) if file_match else "unknown"
            
            # ------ split to chunks ------------------
            
            chunks = splitter.split_text(content)
            
            # ------ create advanced docs ------------------
            
            for i, chunk in enumerate(chunks):
                
                enhanced_metadata = self.metadata(chunk, file_name, i)
                
                doc = Document(
                    page_content=chunk,
                    metadata=enhanced_metadata
                )
                docs.append(doc)
        
        
        
        if docs:
            
            vstore = FAISS.from_documents(docs, self.embeddings, distance_strategy="COSINE", normalize_L2=True)
            return vstore
        
        else:
            logger.error("No documents to index!")
            raise ValueError("No documents found to build vector store")

    def search(self, query: str, k: int = 4, filters: Dict = None) -> Dict:
        
        start_time = time.time()
        
        # ------ similarity search ------------------
            
        try:
            # Get more results to allow for filtering and re-ranking
            raw_results = self.vstore.similarity_search_with_score(query, k=k*2)
            

            # Re-rank results using enhanced scoring
            results = self.sort_search(raw_results, query)[:k]
        
        except Exception as e:

            logger.error(f"Enhanced search error: {str(e)}")

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
        
        for doc, enhanced_score in results:
            # Note: enhanced_score is already a similarity score (0-1), not a distance
            # So we don't need to convert it again with self.similarity()
            docs.append(doc.page_content)
            scores.append(enhanced_score)
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
            "top_score": max(scores) if scores else None,  # Using similarity now (higher = better)
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
        
        if avg_score < 0.2:  # Very low similarity → poor match
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
        
        return result

    def sort_search(self, results: List, query: str) -> List:
        
        enhanced_results = []
        
        for doc, raw_score in results:

            enhanced_score = self.similarity(raw_score, query, doc.page_content, doc.metadata)
            enhanced_results.append((doc, enhanced_score))
        
        enhanced_results.sort(key=lambda x: x[1], reverse=True)
        
        return enhanced_results
    
    # ------------- helpers -------------------------------------------

    def parse_html(self):
        
        doc_count = 0
        
        for file in Path("./Data/phase2_data").glob("*.html"):
            try:
                file_name = file.stem
                
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
                        section_text = f"[**כותרת**: {section_title}] {' '.join(content)}"
                        sections.append(f"[**קובץ**: {file_name}] {section_text}")
                
                # ------- Divide : paragraph (if no headers) ---------------------

                if not sections:
                    for p in soup.find_all('p'):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:  # Skip very short paragraphs
                            sections.append(f"[**קובץ**: {file_name}] {text}")
                
                # ------- Get all Text (no paragraphs) ----------------------------

                if not sections:
                    text = soup.get_text(separator=' ', strip=True)
                    text = re.sub(r'\s+', ' ', text)
                    if text:
                        sections.append(f"[**קובץ**: {file_name}] {text}")
                
                doc_count += 1

                logger.info(f"Processed {file_name}: {len(sections)} sections")
                
                for section in sections:
                    yield section
                    
            except Exception as e:
                logger.error(f"Error processing {file}: {str(e)}")
                continue
        
        logger.info(f"Total documents processed: {doc_count}")

    def get_stats(self) -> Dict:
        
        # ---- avg retrieval time ----------------------------

        retrieval_times = [s["retrieval_time_ms"] for s in self.search_history]
        avg_retrieval_ms = sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0
        
        # ---- quality metrics ----------------------------

        similarity_scores = [s.get("avg_similarity_score", 0) for s in self.search_history]
        
        poor_quality_count = sum(1 for score in similarity_scores if score < 0.3)
        good_quality_count = sum(1 for score in similarity_scores if score >= 0.7)
        
        # ---- content type analysis ----------------------------
        
        content_type_usage = {}
        for s in self.search_history:
            for result in s.get("results_preview", []):
                content_type = result.get("metadata", {}).get("content_type", "unknown")
                content_type_usage[content_type] = content_type_usage.get(content_type, 0) + 1
        
        return {
            "search_performance": {
                "total_searches": self.search_count,
                "avg_retrieval_ms": avg_retrieval_ms,
                "avg_similarity_score": sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0,
            },
            "quality_metrics": {
                "poor_quality_count": poor_quality_count,
                "good_quality_count": good_quality_count,
                "poor_quality_rate": poor_quality_count / self.search_count if self.search_count > 0 else 0,
                "good_quality_rate": good_quality_count / self.search_count if self.search_count > 0 else 0,
            },
            "content_analysis": {
                "content_type_usage": content_type_usage,
                "total_documents": self.vstore.index.ntotal if hasattr(self.vstore, 'index') else 0,
            }
        }

    def base_similarity(self, distance: float) -> float:
        
        sim = 0.8 - (distance / 2.0) 
        return max(0.0, min(1.0, sim))
    
    def similarity(self, raw_score: float, query: str, content: str, metadata: Dict) -> float:
        
        # ------ base similarity -----------------------------
        
        base_score = self.base_similarity(raw_score)
        
        # ------ term similarity  ----------------------------
        
        query_terms = query.lower().split()
        content_lower = content.lower()
        exact_matches = sum(1 for term in query_terms if term in content_lower)
        boosted_score = (exact_matches / len(query_terms)) * 0.2 if query_terms else 0
        
        # ------ content type similarity  -------------------
        
        content_type_boost = 0
        if 'pricing' in query.lower() and metadata.get('has_pricing', False):
            content_type_boost = 0.15
        elif 'contact' in query.lower() and metadata.get('has_contact', False):
            content_type_boost = 0.15
        elif any(term in query.lower() for term in ['table', 'list', 'structured']) and metadata.get('has_structured_data', False):
            content_type_boost = 0.1
        
        # ------ quality -------------------------------------

        quality_boost = metadata.get('quality_score', 0.5) * 0.1
        
        # ------ combined score ------------------------------
        
        enhanced_score = base_score + boosted_score + content_type_boost + quality_boost 
        
        return max(0.0, min(1.0, enhanced_score))
    
    # ------------- metadata -------------------------------------------

    def metadata(self, chunk: str, hmo_name: str, chunk_index: int) -> Dict:
        
        # ------ basic metadata ----------------------------
        
        metadata = {
            "hmo": hmo_name,
            "chunk_index": chunk_index,
            "source": f"{hmo_name}_chunk_{chunk_index}",
            "timestamp": datetime.now().isoformat(),
            "chunk_length": len(chunk)
        }
        
        # ------ content type ----------------------------
        
        content_type = self.content_type(chunk)
        metadata["content_type"] = content_type
        
        # ------ headers ----------------------------
        
        headers = re.findall(r'\[כותרת: ([^\]]+)\]', chunk)
        if headers:
            metadata["section_title"] = headers[0]
            metadata["has_headers"] = True
        else:
            metadata["has_headers"] = False
        
        # ------ pricing/financial information ----------------------------
        
        metadata["has_pricing"] = self.has_financial_content(chunk)
        
        # ------ contact information ----------------------------
        
        metadata["has_contact"] = self.has_contact_info(chunk)
        
        # ------ lists/tables ----------------------------
        
        metadata["has_structured_data"] = self.has_structured_content(chunk)
        
        # ------ content quality score ----------------------------
        
        metadata["quality_score"] = self.content_quality(chunk)
        
        return metadata
    
    def content_type(self, content: str) -> str:

        
        # ------ indicators ----------------------------
        
        has_table_indicators = bool(re.search(r'[|:].*[|:]', content))
        has_list_indicators = content.count('\n') > 2 and ('•' in content or content.count(':') > 3)
        has_pricing = self.has_financial_content(content)
        has_contact = self.has_contact_info(content)
        
        # ------ classify ----------------------------
        
        if has_table_indicators and has_pricing:
            return "pricing_table"
        elif has_table_indicators:
            return "table"
        elif has_list_indicators:
            return "list"
        elif has_contact:
            return "contact"
        elif has_pricing:
            return "pricing"
        else:
            return "text"
    
    def content_quality(self, content: str) -> float:
          
        # ------ length quality ----------------------------
        
        length_score = min(1.0, len(content) / 500)  # Normalize to 500 chars
        if len(content) < 10:
            length_score *= 0.5  # Penalty for very short content
        
        # ------ information density ----------------------------
        
        meaningful_chars = len(re.sub(r'[^\w\s]', '', content))
        density_score = meaningful_chars / len(content) if content else 0
        
        # ------ structure quality ----------------------------
        
        structure_score = 0.5
        if '[כותרת:' in content:
            structure_score += 0.3
        if self.has_structured_content(content):
            structure_score += 0.2
        
        # ------ overall quality ----------------------------
        
        quality = (length_score * 0.4 + density_score * 0.3 + structure_score * 0.3)
        return min(1.0, quality)

    def has_financial_content(self, content: str) -> bool:
        
        financial_indicators = [
            '%', '₪', 'חינם', 'הנחה', 'מחיר', 'עלות', 'תשלום', 'כספי'
        ]
        
        return any(indicator in content for indicator in financial_indicators)
    
    def has_contact_info(self, content: str) -> bool:
        
        contact_patterns = [
            r'\d{2,4}[-*]\d{3,4}[-*]\d{3,4}',  # Phone numbers
            r'\d{4}\*',  # Short codes
            r'@\w+\.\w+',  # Email
            r'https?://\w+',  # URLs
            r'טלפון', r'מייל', r'אתר'  # Contact words
        ]
        
        return any(re.search(pattern, content) for pattern in contact_patterns)
    
    def has_structured_content(self, content: str) -> bool:
        
        structure_indicators = [
            content.count(':') > 3,  # Many colons suggest structured data
            content.count('|') > 2,  # Pipe separators
            content.count('\n') > 5 and content.count(':') > 2,  # Lists with descriptions
            bool(re.search(r'^\s*\d+\.', content, re.MULTILINE))  # Numbered lists
        ]
        
        return any(structure_indicators)
    

# ------------- initialize rag --------------------------------------

rag = RAG()