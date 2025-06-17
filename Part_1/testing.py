from dotenv import load_dotenv; load_dotenv()
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
import os

# --------- Env Variables ----------------------------------------------

doc_int_key = os.getenv("AZURE_DOC_INT_KEY")
doc_int_endpoint = os.getenv("AZURE_DOC_INT_ENDPOINT")

openai_key = os.getenv("AZURE_OPENAI_KEY")
openai_version = os.getenv("AZURE_OPENAI_VERSION")
openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

gpt4o_endpoint = os.getenv("GPT4o_ENDPOINT")
gpt4o_mini_endpoint = os.getenv("GPT4o_MINI_ENDPOINT")

# --------- Document Intelligence --------------------------------------

def test_document_intelligence():

    # --- example doc -------------

    path = "Data/phase1_data/283_ex1.pdf"
    content = "" 
    
    with open(path, "rb") as f:
        content = f.read()

    # --- API instances -------------

    client = DocumentIntelligenceClient(
            endpoint=doc_int_endpoint,
            credential=AzureKeyCredential(doc_int_key)
        )
        
    poller = client.begin_analyze_document(
        "prebuilt-layout",  
        content
    )

    # --- result -------------
        
    result = poller.result()
    print(f"   Result: {result.content[:100]}")

    return True

# --------- OpenAI -----------------------------------------------------

def test_azure_openai():    

    # --- API instances -------------

    client = AzureOpenAI(
        api_key=openai_key,
        api_version=openai_version,
        azure_endpoint=openai_endpoint
    )

    embedding_response = client.embeddings.create(
        model="text-embedding-ada-002",  # Make sure this matches your deployment name
        input="Test embedding text"
    )
    
    # --- API instances -------------

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "say hi there"}
        ],
        max_tokens=100,
        temperature=0.1
    )
    
    # Test embeddings
    
    print(f"   Response: {response.choices[0].message.content}")
    print(f"   Embedding: {len(embedding_response.data[0].embedding)}")
    
    return True
        


if __name__ == "__main__":
    
    test_azure_openai()
    test_document_intelligence()