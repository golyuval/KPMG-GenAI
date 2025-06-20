from fastapi import APIRouter, HTTPException, Header
from datetime import datetime
from pathlib import Path
import json
import time
import sys

from schemas import Request, Response
from services import (
    collect, verify, validate_input, get_qa_chain, cleanup_old_sessions,
    session_chains, session_last_access, token_usage
)
import rag
from Core.logger_setup import get_logger
from Core import config

# ------------- logger ----------------------------------------------

logger = get_logger(__name__)

# ------------- router ----------------------------------------------

router = APIRouter()

# ------------- health route ----------------------------------------

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(session_chains),
        "timestamp": datetime.now().isoformat()
    }

# ------------- main route ------------------------------------------

@router.post("/chat", response_model=Response)
async def chat(req: Request):
    
    try:
        
        # --- validate non malicious content --------------------------

        user_msg = validate_input(req.user_msg)
        if user_msg != req.user_msg:
            return Response(assistant_msg=user_msg, user_info=req.user_info)
        
        # Get user ID for tracking
        user_id = req.user_info.get("id_number") if req.user_info else "anonymous"
        logger.info(f"Processing request from {user_id}: {req.user_msg[:50]}...")
        
        # --- clean sessions -------------------------------------------

        if len(session_chains) > 50:
            cleanup_old_sessions()
        
        # ---------- phase 1 : collection ------------------------------
        
        if not req.user_info:
            
            assistant, info = collect(req.history, req.user_msg)
            
            return Response(assistant_msg=assistant, user_info=info)
        
        # ---------- phase 1.5 : verification --------------------------
        
        elif req.user_info and not req.user_info.get("verified", False):

            assistant, updated_info, is_verified = verify(req.history, req.user_msg, req.user_info)
            
            if is_verified:
                updated_info["verified"] = True
                
            return Response(assistant_msg=assistant, user_info=updated_info)

        # ---------- phase 2 : QA --------------------------------------
        
        else:
            
            # ----- get session ID --------------------------
        
            session_id = req.user_info.get("id_number", f"temp_{int(time.time())}")
            
            if session_id not in session_chains:
                session_chains[session_id] = get_qa_chain(session_id)
                logger.info(f"Created new session for {session_id}")
            
            session_last_access[session_id] = time.time()
            
            # ----- perform retrieval -----------------------
            
            user_language = req.user_info.get("language", "he")
            retrieved_docs = rag.rag.search(req.user_msg, k=4)
            user_context = json.dumps(req.user_info, ensure_ascii=False)
            
            # ----- run chain -------------------------------
        
            qa_chain = session_chains[session_id]
            result = qa_chain({
                "question": req.user_msg,
                "user_info": user_context,
                "hmo_name": req.user_info.get("hmo_name", "לא ידוע"),
                "tier": req.user_info.get("tier", "לא ידוע"),
                "json_format": config.chatbot_format_qa,
                "language": "Hebrew" if user_language == "he" else "English"
            })
            
            answer = result.get("answer", "מצטער, לא הצלחתי למצוא תשובה.")

            # Extract assistant_message if it's still in JSON format
            try:
                if answer.startswith('{') and answer.endswith('}'):
                    parsed_answer = json.loads(answer)
                    answer = parsed_answer.get("assistant_message", answer)
            except json.JSONDecodeError:
                pass  

            # ----- format citations -----------------------

            if retrieved_docs["documents"]:
                citations_text = "\n\n**מקורות:**\n"
                
                # Get metadata from RAG search results
                rag_results = retrieved_docs.get("metadata", {}).get("results_preview", [])
                
                for i, doc_info in enumerate(rag_results[:3], 1):
                    hmo = doc_info.get("metadata", {}).get("hmo", "לא ידוע")
                    content_preview = doc_info.get("content", "")[:120] + "..." if len(doc_info.get("content", "")) > 120 else doc_info.get("content", "")
                    score = doc_info.get("score", 0)
                    
                    citations_text += f"[{i}] {hmo} (רלוונטיות: {score:.2f}): {content_preview}\n"
                
                final_answer = answer + citations_text
            else:
                final_answer = answer + "\n\n**לא נמצאו מקורות תומכים**"
            
            logger.info(f"Retrieval quality - Avg score: {retrieved_docs['metadata']['avg_similarity_score']:.3f}")
            
            return Response(assistant_msg=final_answer, user_info=req.user_info)
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="שגיאת שרת פנימית")

# ------------- stats routes ----------------------------------------

@router.get("/token-usage")
async def get_token_usage():
    """Get token usage statistics"""
    return {
        "token_usage": token_usage,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/rag-stats")
async def get_rag_stats():
    try:
        return {
            "search_count": rag.rag.search_count,
            "cache_stats": rag.rag.get_cache_stats(),
            "recent_searches": rag.rag.search_history[-10:] if hasattr(rag.rag, 'search_history') else []
        }
    except Exception as e:
        logger.error(f"Error getting RAG stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving RAG statistics")
    
@router.get("/logs/info")
async def get_info_logs(
    lines: int = 100,
    api_key: str = Header(None, alias="X-API-Key")
):
    """Get recent info logs"""
    
    try:
        # Get the correct path
        server_dir = Path(__file__).parent
        part2_dir = server_dir.parent
        log_file = part2_dir / "Log" / "log_info.log"
        
        logger.info(f"Checking log file at: {log_file.absolute()}")
        
        if not log_file.exists():
            return {
                "error": "Log file not found",
                "tried_path": str(log_file.absolute()),
                "working_dir": str(Path.cwd())
            }
        
        # Read last N lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
        return {
            "logs": [line.strip() for line in recent_lines],
            "total_lines": len(all_lines),
            "requested_lines": lines,
            "file_path": str(log_file.absolute())
        }
        
    except Exception as e:
        logger.error(f"Error reading info logs: {str(e)}")
        return {"error": f"Error reading logs: {str(e)}"}

@router.get("/logs/errors")
async def get_error_logs(
    lines: int = 50,
    api_key: str = Header(None, alias="X-API-Key")
):
    """Get recent error logs"""
    
    try:
        # Same path resolution
        server_dir = Path(__file__).parent
        part2_dir = server_dir.parent
        log_file = part2_dir / "Log" / "log_error.log"
        
        if not log_file.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.touch()
            return {
                "logs": [],
                "message": "No errors logged yet",
                "file_created": True
            }
        
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
        return {
            "logs": [line.strip() for line in recent_lines],
            "total_errors": len(all_lines),
            "requested_lines": lines
        }
        
    except Exception as e:
        logger.error(f"Error reading error logs: {str(e)}")
        return {"error": f"Error reading error logs: {str(e)}"}