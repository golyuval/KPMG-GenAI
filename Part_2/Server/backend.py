from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from langchain_openai import AzureChatOpenAI
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from Server import rag
from Core import config

import json

app = FastAPI(title="HMO Chatbot", version="0.1-alpha")

llm = AzureChatOpenAI(
    azure_endpoint=config.openai_endpoint,
    api_key=config.openai_key,
    deployment_name=config.openai_model_mini,
    api_version=config.openai_version,
    temperature=0.3,
)

# -------- collection chain -----------------

collect_chain = llm  

# -------- RAG chain ----------------------

qa_chain = ConversationalRetrievalChain.from_llm(
    llm,
    rag.rag.vstore.as_retriever(search_kwargs={"k": 4}),
    return_source_documents=False,
)

# -------- request / response models ----------------------

class Request(BaseModel):
    history: List[Dict[str, str]] = Field(default_factory=list)
    user_info: Dict[str, Any] | None = None
    user_msg: str

class Response(BaseModel):
    assistant_msg: str
    user_info: Dict[str, Any] | None = None

# ---------------- helper -------------------------------------

def collect(history, user_msg):

    msgs = [
        {"role": "system", "content": config.chatbot_system_collection},
        *history,
        {"role": "user", "content": user_msg},
    ]

    out = llm.invoke(msgs).content
    info_json, assistant = None, out

    if "###INFO_END###" in out:

        json_part = out.split("{" ,1)[1].split("}",1)[0] + "}"
        info_json = json.loads(json_part)
        assistant = out.replace(json_part, "").replace("###INFO_END###", "").strip()

    return assistant, info_json

# ---------------- endpoint ---------------------------------------

@app.post("/chat", response_model=Response)
async def chat(req: Request):

    # ------- collection phase -----------------
    
    if not req.user_info:
        assistant, info = collect(req.history, req.user_msg)
        return Response(assistant_msg=assistant, user_info=info)
    
    # ------- QA phase -----------------

    else:

        user_context = json.dumps(req.user_info, ensure_ascii=False)
        system = config.chatbot_system_qa.format(info=user_context)
        answer = qa_chain.run(
            {
                "question": req.user_msg,
                "chat_history": req.history, 
                "system": system
            })

        return Response(assistant_msg=answer, user_info=req.user_info)
    