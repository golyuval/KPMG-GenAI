import re
from typing import Any, Dict
from langchain_openai import AzureChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
import time
import json

from Core import config
from Core.logger_setup import get_logger
from schemas import UserInfoResponse, VerificationResponse
import rag

# ------------- logger ----------------------------------------------

logger = get_logger(__name__)

# ------------- language detection ----------------------------------

def detect_language(text: str) -> str:
    
    if not text:
        return "en"
    
    # Count Hebrew characters
    hebrew_chars = sum(1 for c in text if '\u0590' <= c <= '\u05FF')
    total_chars = len(text.strip())
    
    # If more than 30% Hebrew characters, it's Hebrew
    if total_chars > 0 and (hebrew_chars / total_chars) > 0.3:
        return "he"
    return "en"

def get_language_prompt(language: str) -> str:
    
    if language == "he":
        return "Answer in Hebrew only."
    return "Answer in English only."

# ------------- GPT-4o (chatbot) -----------------------------------

llm = AzureChatOpenAI(
    azure_endpoint=config.openai_endpoint,
    api_key=config.openai_key,
    deployment_name=config.openai_model_mini,
    api_version=config.openai_version,
    temperature=0.3,
)

# ------------- parsers ---------------------------------------------

collection_parser = PydanticOutputParser(pydantic_object=UserInfoResponse)
verification_parser = PydanticOutputParser(pydantic_object=VerificationResponse)

# ------------- token tracking --------------------------------------

token_usage = {
    "gpt-4o-mini": {"prompt_tokens": 0, "completion_tokens": 0, "total_cost": 0},
    "text-embedding-ada-002": {"total_tokens": 0, "total_cost": 0}
}
token_pricing = {
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "text-embedding-ada-002": 0.00001
}

session_chains = {}
session_last_access = {}
SESSION_TIMEOUT = 1800  # 30 min

# ------------- phase 1 - collection ----------------------------------

def validate_user_info(info: Dict[str, Any], required_fields) -> bool:
            
            
    # --- collection completion check --------------------------

    if not info.get("collection_complete", False):
        return False
        
    # --- collection completion check --------------------------

    all_filled = all(
        info.get(field) and str(info.get(field)).strip() 
        for field in required_fields
    )
                
    if not all_filled or not all(field in info for field in required_fields):
        return False
    
    # --- ID validation ---------------------------

    if not re.match(r'^\d{9}$', str(info.get("id_number", ""))):
        return False
    
    # --- age validation ---------------------------
    
    age = info.get("age")
    try:
        age_int = int(age) if isinstance(age, str) else age
        if not (0 <= age_int <= 120):
            return False
    except:
        return False
    
    # --- HMO validation ---------------------------
    
    if info.get("hmo_name") not in config.validation_hmo:
        return False
    
    # --- tier validation ---------------------------
    
    if info.get("tier") not in config.validation_tiers:
        return False
    
    return True

def validate_input(user_input: str) -> str:
    
    dangerous_patterns = [
        "ignore previous instructions",
        "disregard the system prompt",
        "you are now",
        "forget everything",
        "system:",
        "assistant:",
        "###"
    ]
    
    lower_input = user_input.lower()
    for pattern in dangerous_patterns:
        if pattern in lower_input:
            logger.warning(f"Potential injection attempt: {pattern}")
            return "אנא נסח מחדש את השאלה שלך."
    
    return user_input

def collect(history, user_msg):

    logger.info(f"Starting collection phase for message: {user_msg[:50]}...")
    
    try:

        # --- invoke LLM --------------------------
        
        user_language = detect_language(user_msg)
        language_instruction = get_language_prompt(user_language)
        logger.info(f"Detected language: {user_language} for collection phase")

        formatted_prompt = config.chatbot_system_collection.format(
            info=config.chatbot_format_user_info
        ) + f"\n\n{language_instruction}"
        
        msgs = [
            {"role": "system", "content": formatted_prompt},
            *history,
            {"role": "user", "content": user_msg},
        ]

        response = llm.invoke(msgs, response_format={"type": "json_object"})
        out = response.content

        # --- track tokens --------------------------

        if hasattr(response, 'response_metadata'):
            usage = response.response_metadata.get('token_usage', {})
            if usage:
                token_usage["gpt-4o-mini"]["prompt_tokens"] += usage.get('prompt_tokens', 0)
                token_usage["gpt-4o-mini"]["completion_tokens"] += usage.get('completion_tokens', 0)
                
                prompt_cost = (usage.get('prompt_tokens', 0) / 1000) * token_pricing["gpt-4o-mini"]["prompt"]
                completion_cost = (usage.get('completion_tokens', 0) / 1000) * token_pricing["gpt-4o-mini"]["completion"]
                token_usage["gpt-4o-mini"]["total_cost"] += prompt_cost + completion_cost
                
                logger.info(f"Token usage - Prompt: {usage.get('prompt_tokens', 0)}, Completion: {usage.get('completion_tokens', 0)}")
                logger.info(f"Collection raw output: {out}")
        
        # --- validate results --------------------------
        
        result = json.loads(out)
        
        if validate_user_info(result,config.user_info_required_fields):
            
            user_info = {k: v for k, v in result.items() if k in config.user_info_required_fields}
            user_info["language"] = user_language  
            return result.get("assistant_message", "תודה!"), user_info
        
        return result.get("assistant_message", "תודה!"), None

        
    
    except Exception as e:
        logger.error(f"Error in collect: {str(e)}")
        return "מצטער, נתקלתי בבעיה.", None

# ------------- phase 1.5 - verification ------------------------------

def verify(history, user_msg, current_info):

    logger.info(f"Starting verification phase for user: {current_info.get('id_number', 'unknown')}")
    
    try:

        # --- invoke LLM ------------------------------------

        current_info_str = json.dumps(current_info, ensure_ascii=False, indent=2)

        user_language = current_info.get("language", detect_language(user_msg))
        language_instruction = get_language_prompt(user_language)
        logger.info(f"Using language: {user_language} for verification phase")

        formatted_prompt = config.chatbot_system_verification.format(
            current_info=current_info_str,
            json_format=config.chatbot_format_user_info
        ) + f"\n\n{language_instruction}"
        
        msgs = [
            {"role": "system", "content": formatted_prompt},
            *history,
            {"role": "user", "content": user_msg},
        ]

        out = llm.invoke(msgs, response_format={"type": "json_object"}).content
        logger.info(f"Verification raw output: {out}")
        
        # --- verification check -----------------------------

        try:

            result = json.loads(out)

            # --- verified - next phase --------------------------
            
            if result.get("verified", False):
                user_info = {k: v for k, v in result.items() if k in config.user_info_required_fields}
                user_info["verified"] = True
                user_info["language"] = user_language  
                return result.get("assistant_message", "מעולה!"), user_info, True
            
            # --- not verified - stay on same phase --------------
            
            else:
                user_info = {k: v for k, v in result.items() if k in config.user_info_required_fields}
                return result.get("assistant_message", "בוא נבדק שוב."), user_info, False
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification JSON: {e}")
            return "בוא ננסה שוב.", current_info, False
    
    except Exception as e:
        logger.error(f"Error in verify: {str(e)}")
        return "מצטער, נתקלתי בבעיה.", current_info, False
    
# ------------- phase 2 - Q and A -------------------------------------

def get_qa_chain(session_id: str):
    
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
        input_key="question"  
    )
    
    # Use the config prompt instead of hardcoded one
    qa_prompt = PromptTemplate(
        template=config.chatbot_system_qa,
        input_variables=["context", "user_info", "question", "hmo_name", "tier"]
    )
    
    return ConversationalRetrievalChain.from_llm(
        llm,
        rag.rag.vstore.as_retriever(search_kwargs={"k": 4}),
        return_source_documents=True,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": qa_prompt}
    )

def cleanup_old_sessions():
    
    # --- find expired sessions -------------------------

    current_time = time.time()
    expired = [
        sid for sid, last_access in session_last_access.items()
        if current_time - last_access > config.session_timeout
    ]

    # --- delete expired sessions -------------------------

    for sid in expired:
        if sid in session_chains:
            del session_chains[sid]
        if sid in session_last_access:
            del session_last_access[sid]
    
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired sessions")


# ------------- exports for routes ----------------------------------

__all__ = [
    'collect',
    'verify', 
    'validate_input',
    'get_qa_chain',
    'cleanup_old_sessions',
    'session_chains',
    'session_last_access',
    'token_usage',
    'llm'
]