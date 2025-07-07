import re
from typing import Any, Dict
from langchain_openai import AzureChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import PromptTemplate
import time
import json
from langdetect import detect, LangDetectException

from Server import config
from Core.logger import get_logger
from schemas import UserInfoResponse, VerificationResponse
import rag
import json, time


# ------------- logger ----------------------------------------------

logger = get_logger(__name__)

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
    
    "gpt-4o-mini": 
    {
        "prompt_tokens": 0, 
        "completion_tokens": 0, 
        "total_cost": 0
    },

    "text-embedding-ada-002": 
    {
        "total_tokens": 0,
        "total_cost": 0
    }
}

token_pricing = {

    "gpt-4o-mini": 
    {
        "prompt": 0.00015,
        "completion": 0.0006
    },

    "text-embedding-ada-002": 0.00001
}

session_chains = {}
session_last_access = {}
SESSION_TIMEOUT = 1800  # 30 min

# ------------- phase 1 - collection ----------------------------------

def collect(history, user_msg, user_info=None):

    logger.info(f"Starting collection phase for message: {user_msg[:50]}...")
    
    try:

        # --- invoke LLM --------------------------
        
        prev_language = user_info.get("language") if user_info else None
        user_language = detect_language(user_msg, prev_language)        
        language_instruction = get_language_prompt(user_language)

        formatted_prompt = config.chatbot_system_collection.format(
            info=config.chatbot_format_user_info
        ) + f"\n\n{language_instruction}"
        
        logger.info("COLLECT prompt:\n%s", formatted_prompt)

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
        
        validation_passed = validate_info(result, config.user_info_required_fields)
        
        if not validation_passed:
            
            result["collection_complete"] = False
            result["verified"] = False

        return result.get("assistant_message", "תודה!"), result

    except Exception as e:
        logger.error(f"Error in collect: {str(e)}")
        return "מצטער, נתקלתי בבעיה.", None

def validate_info(info: Dict[str, Any], required_fields) -> bool:


    all_valid = True
    logger.info(f"DEBUG: Validating info: {info}")
    
    # --- field existance ---------------

    for field in required_fields:
        if field not in info or not info.get(field) :
            logger.info(f"DEBUG: Missing field: {field}")
            info[field] = ""
    
    # --- ID ----------------------------

    if info.get("id_number") != "" and not re.match(r'^\d{9}$', str(info.get("id_number", ""))):
        info["id_number"] = ""
        all_valid = False
    
    # --- age ---------------------------

    if info.get("age") != "":
        try:
            age = info.get("age")
            age_int = int(age) if isinstance(age, str) else age
            if not (0 <= age_int <= 120):
                logger.info(f"DEBUG: Invalid age: {age} - resetting")
                info["age"] = ""
                all_valid = False
        except:
            logger.info(f"DEBUG: Age conversion error: {info.get('age')} - resetting")
            info["age"] = ""
            all_valid = False
    
    # --- HMO ---------------------------

    if info.get("hmo_name") != "" and info.get("hmo_name") not in config.validation_hmo:
        logger.info(f"DEBUG: Invalid HMO: {info.get('hmo_name')} not in {config.validation_hmo} - resetting")
        info["hmo_name"] = ""
        all_valid = False
    
    # --- tier ---------------------------
    
    if info.get("tier") != "" and info.get("tier") not in config.validation_tiers:
        logger.info(f"DEBUG: Invalid tier: {info.get('tier')}")
        info["tier"] = ""
        all_valid = False

    # --- validation done ---------------------------
    
    if all_valid:
        logger.info("All fields validation passed!")
    else:
        logger.info("Some fields were invalid and reset")
    
    return all_valid

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

# ------------- phase 1.5 - verification ------------------------------

def verify(history, user_msg, current_info):

    logger.info(f"Starting verification phase for user: {current_info.get('id_number', 'unknown')}")
    
    try:

        # --- invoke LLM ------------------------------------

        current_info_str = json.dumps(current_info, ensure_ascii=False, indent=2)
        prev_language = current_info.get("language")
        user_language = detect_language(user_msg, prev_language)
        language_instruction = get_language_prompt(user_language)

        formatted_prompt = config.chatbot_system_verification.format(
            current_info=current_info_str,
            json_format=config.chatbot_format_user_info
        ) + f"\n\n{language_instruction}"
        
        logger.info("VERIFY prompt:\n%s", formatted_prompt)
        
        msgs = [
            {"role": "system", "content": formatted_prompt},
            #*history,
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
                user_info["verified"] = False
                user_info["collection_complete"] = result.get("collection_complete", True)  # Should be True at this point
                user_info["language"] = user_language
                return result.get("assistant_message", "בוא נבדק שוב."), user_info, False
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse verification JSON: {e}")
            return "בוא ננסה שוב.", current_info, False
    
    except Exception as e:
        logger.error(f"Error in verify: {str(e)}")
        return "מצטער, נתקלתי בבעיה.", current_info, False
    
# ------------- phase 2 - Q and A -------------------------------------

def answer(history, user_msg, user_info):

    # ----- get session ID --------------------------

    session_id = user_info.get("id_number", f"temp_{int(time.time())}")
    if session_id not in session_chains:
        session_chains[session_id] = get_qa_chain(session_id)
        logger.info(f"Created new session for {session_id}")
    session_last_access[session_id] = time.time()

    # ----- perform retrieval -----------------------

    user_language = detect_language(user_msg, user_info.get("language"))
    user_info["language"] = user_language
    retrieved_docs = rag.rag.search(user_msg, k=4)
    user_context = json.dumps(user_info, ensure_ascii=False)

    # ----- run chain -------------------------------

    qa_chain = session_chains[session_id]
    result = qa_chain({
        "question": user_msg,
        "user_info": user_context,
        "hmo_name": user_info.get("hmo_name", "לא ידוע"),
        "tier": user_info.get("tier", "לא ידוע"),
        "json_format": config.chatbot_format_qa,
        "language": "Hebrew" if user_language == "he" else "English"
    })

    # ----- extract answer ------------------------------

    answer = result.get("answer", "מצטער, לא הצלחתי למצוא תשובה.")
    try:
        if answer.startswith('{') and answer.endswith('}'):
            parsed_answer = json.loads(answer)
            answer = parsed_answer.get("assistant_message", answer)
    except json.JSONDecodeError:
        pass

    # ----- format citations -----------------------

    RELEVANCE_THRESHOLD = 0.25  # Much stricter - ignore truly irrelevant docs
    STRONG_THRESHOLD = 0.7   # High relevance content
    MIDDLE_THRESHOLD = 0.45  # Moderate relevance content

    if retrieved_docs["documents"]:

        citations_text = "\n\n---\n\n# **מקורות רלוונטיים מהמאגר :**\n"
        rag_results = retrieved_docs.get("metadata", {}).get("results_preview", [])
        relevant_found = False

        for i, doc_info in enumerate(rag_results[:3], 1):
            
            # --- check relevance --------------------------

            score = doc_info.get("score", 0)
            if score < RELEVANCE_THRESHOLD:
                continue  # Skip irrelevant docs

            # --- format citation --------------------------

            relevant_found = True
            hmo = doc_info.get("metadata", {}).get("hmo", "לא ידוע")
            content_preview = doc_info.get("content", "")[:120] + "..." if len(doc_info.get("content", "")) > 120 else doc_info.get("content", "")
            
            if score >= STRONG_THRESHOLD:
                relevance_label = f'<span style="color:green">חזק {score:.2f}</span>'
            elif score >= MIDDLE_THRESHOLD:
                relevance_label = f'<span style="color:orange">בינוני {score:.2f}</span>'
            else:
                relevance_label = f'<span style="color:red">חלש {score:.2f}</span>'

            citations_text += f"**[{i}] {hmo} ({relevance_label}) :** {content_preview}\n"

        if relevant_found:
            final_answer = answer + citations_text
        else:
            final_answer = answer + "\n\n**לא נמצאו מקורות רלוונטיים**"
    else:
        final_answer = answer + "\n\n**לא נמצאו מקורות תומכים**"

    logger.info(f"Retrieval quality - Avg score: {retrieved_docs['metadata']['avg_similarity_score']:.3f}")
    return final_answer, user_info

def get_qa_chain(session_id: str):
    
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
        input_key="question"  
    )
    
    
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

# ------------- language detection ----------------------------------

def detect_language(text: str, prev_language: str = None) -> str:
    try:
        # --- empty or digits --------------------------
        
        if not any(c.isalpha() for c in text):
            logger.info(f"Language detection skipped (no alpha chars): '{text}'")
            return prev_language or "he"
        
        # --- Hebrew detection --------------------------
        
        has_hebrew = any(0x0590 <= ord(c) <= 0x05FF for c in text)
        
        if has_hebrew:
            logger.info(f"Hebrew characters detected in text: '{text}'")
            return "he"
        else:
            logger.info(f"No Hebrew characters detected, assuming English for text: '{text}'")
            return "en"
            
    except Exception as e:
        logger.warning(f"Language detection failed for text: '{text}'. Exception: {e}")
        return prev_language or "en"

def get_language_prompt(language: str) -> str:
    
    if language == "he":
        return "Answer in Hebrew only."
    return "Answer in English only."


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