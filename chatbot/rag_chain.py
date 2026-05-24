import logging
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)
_rag_retriever = None

def build_knowledge_retriever():
    global _rag_retriever
    if _rag_retriever is not None:
        return _rag_retriever
    try:
        from chatbot.modules.trading_assistant import TRADING_KNOWLEDGE
        docs = [Document(
            page_content=e.get("title","") + "\n" + e.get("content",""),
            metadata={"key": k, "title": e.get("title", k)}
        ) for k, e in TRADING_KNOWLEDGE.items()]
        splits = RecursiveCharacterTextSplitter(
            chunk_size=600, chunk_overlap=60
        ).split_documents(docs)
        vstore = FAISS.from_documents(
            splits, HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        )
        _rag_retriever = vstore.as_retriever(search_kwargs={"k": 2})
        logger.info(f"RAG retriever ready — {len(splits)} chunks from {len(docs)} topics")
        return _rag_retriever
    except Exception as e:
        logger.error(f"RAG build failed: {e}")
        return None

def get_rag_retriever():
    return build_knowledge_retriever()

def get_wikipedia_summary(company_name: str) -> str:
    try:
        import urllib.request, json, urllib.parse
        q = urllib.parse.quote(company_name)
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{q}"
        req = urllib.request.Request(url, headers={"User-Agent": "FinSight/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read()).get("extract", "")[:500]
    except Exception:
        return ""
