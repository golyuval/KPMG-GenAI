"""LangChain RAG components – <30 lines."""
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from pathlib import Path
from bs4 import BeautifulSoup
from Core import config



class RAG:

    def __init__(self):
        self.vstore = self.build()

    def html_docs(self):

        for file in Path("../../Data/phase2_data").glob("*.html"):

            hmo = file.stem
            txt = BeautifulSoup(file.read_text(encoding="utf8"), "lxml").get_text(" ")
            yield f"[HMO={hmo}] " + " ".join(txt.split())

    def build(self):

        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        docs = splitter.create_documents(list(self.html_docs()))

        emb = AzureOpenAIEmbeddings(
            azure_endpoint=config.openai_endpoint,
            api_key=config.openai_key,
            deployment=config.openai_model_mini,
            api_version=config.openai_version,
        )

        return FAISS.from_documents(docs, emb)

    def top_k(self, query: str, k: int = 4):
        return [d.page_content for d in self.vstore.similarity_search(query, k=k)]

rag = RAG()

