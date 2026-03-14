from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import JSONLoader
from langchain_core.prompts import ChatPromptTemplate
import os
import json
from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda

load_dotenv()

# ✅ Load greeting data
loader = JSONLoader(
    file_path=os.path.join(os.path.dirname(__file__), "data", "greeting_data.json"),
    jq_schema=".[]",
    text_content=False,
    metadata_func=lambda record, _: {"inputs": record.get("inputs", [])}
)


documents = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
docs = splitter.split_documents(documents)

# ✅ Embed & store
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(docs, embeddings)
retriever = vectorstore.as_retriever()

# ✅ Load LLM (Groq)
raw_llm = ChatGroq(
    groq_api_key=os.environ["GROQ_API_KEY"],
    model_name="llama-3.1-8b-instant"
)

financial_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are FinSight — an expert financial assistant.\n"
     "Always respond concisely using correct financial terms.\n"
     "Explain clearly using minimal but informative language.\n"
     "Avoid long paragraphs. Prefer bullet points or short definitions.\n"
     "Give real-world trading examples when useful."
     
     ),
    ("human", "{input}")
])

llm_chain = financial_prompt | raw_llm
# ✅ Smart router: greetings = RAG, else LLM
def custom_qa_chain(user_input: str) -> str:
    input_lower = user_input.lower()

    # ✅ Check using retriever (instead of hardcoded GREETING_KEYWORDS)
    relevant_docs = retriever.invoke(user_input)


    for doc in relevant_docs:
        inputs = doc.metadata.get("inputs", [])
        if any(phrase.lower() in input_lower for phrase in inputs):
            try:
                parsed = json.loads(doc.page_content)
                return parsed.get("content", "👋 Hello! How can I help you today?")
            except Exception as e:
                print("❌ Failed to parse RAG response:", e)
                return "👋 Hello! How can I help you today?"

    # ❗Fallback to general LLM
    print("💬 Using LLM response")
    response = llm_chain.invoke({"input": user_input})

    return response.content if hasattr(response, "content") else str(response)


# ✅ Exported function & retriever (in case you need them separately)
qa_chain = custom_qa_chain

# 👇 Add this so you can import retriever separately if needed
def get_retriever():
    return retriever
