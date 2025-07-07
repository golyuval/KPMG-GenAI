from fastapi import APIRouter, HTTPException, Header
from datetime import datetime
from pathlib import Path
import json
import time
import sys

from schemas import Request, Response
from services import (
    collect, verify, validate_input, get_qa_chain, cleanup_old_sessions,
    session_chains, session_last_access, token_usage, answer
)
import rag
from Core.logger import get_logger
from Server import config

# ------------- logger ----------------------------------------------

logger = get_logger(__name__)

# ------------- router ----------------------------------------------

router = APIRouter()

# ------------- health route ----------------------------------------

@router.get("/health")
async def health_check():
    
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
        
       
        if req.user_info is None:
            req.user_info = {"verified": False, "collection_complete": False}
        
        user_id = req.user_info.get("id_number", "anonymous")
        logger.info(f"Processing request from {user_id}: {req.user_msg[:50]}...")
        
        # Debug: Log the user_info state and which phase we're entering
        logger.info(f"DEBUG: req.user_info = {req.user_info}")
        logger.info(f"DEBUG: user_info.get('verified'): {req.user_info.get('verified', False)}")
        logger.info(f"DEBUG: user_info.get('collection_complete'): {req.user_info.get('collection_complete', False)}")

        # --- clean sessions -------------------------------------------

        if len(session_chains) > 50:
            cleanup_old_sessions()
        
        # --- phase 1 : collection ------------------------------
        
        if not req.user_info.get("collection_complete", False):
            logger.info("DEBUG: Entering COLLECTION phase")
            assistant, info = collect(req.history, req.user_msg, req.user_info)
            logger.info(f"DEBUG: Collection returned user_info: {info}")
            return Response(assistant_msg=assistant, user_info=info)
        
        # --- phase 1.5 : verification --------------------------
        
        elif not req.user_info.get("verified", False):
            logger.info("DEBUG: Entering VERIFICATION phase")
            assistant, updated_info, is_verified = verify(req.history, req.user_msg, req.user_info)
            
            if is_verified:
                updated_info["verified"] = True
                
            return Response(assistant_msg=assistant, user_info=updated_info)

        # --- phase 2 : answer questions --------------------------------------
        
        else:
            logger.info("DEBUG: Entering Q&A phase")
            assistant_msg, new_info = answer(req.history, req.user_msg, req.user_info)

            return Response(assistant_msg=assistant_msg, user_info=new_info)
            
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="שגיאת שרת פנימית")

# ------------- stats routes ----------------------------------------

@router.get("/token-usage")
async def get_token_usage():
    
    return {
        "token_usage": token_usage,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/rag-stats")
async def get_rag_stats():
    try:
        return {
            "search_count": rag.rag.search_count,
            "stats": rag.rag.get_stats(),
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
    
    try:
        
        # --- get log file --------------------------------------------
        
        server_dir = Path(__file__).parent
        part2_dir = server_dir.parent
        log_file = part2_dir / "Log" / "info.log"
        
        logger.info(f"Checking log file at: {log_file.absolute()}")
        
        # --- no log file ----------------------------------------------
        
        if not log_file.exists():
            return {
                "error": "Log file not found",
                "tried_path": str(log_file.absolute()),
                "working_dir": str(Path.cwd())
            }
        
        # --- read log file --------------------------------------------
        
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
        
        # --- get log file --------------------------------------------

        server_dir = Path(__file__).parent
        part2_dir = server_dir.parent
        log_file = part2_dir / "Log" / "error.log"

        # --- no log file ----------------------------------------------
        
        if not log_file.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.touch()
            return {
                "logs": [],
                "message": "No errors logged yet",
                "file_created": True
            }
        
        # --- read log file --------------------------------------------
        
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