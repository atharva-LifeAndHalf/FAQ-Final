# rag_engine.py

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.document_loaders import UnstructuredExcelLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

load_dotenv()
gemini_key = os.getenv("gemini_key")

# ---- Initialize LLM ----
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=gemini_key
)

# ---- Load Excel ----
loader = UnstructuredExcelLoader("C://Users//ss//OneDrive//Desktop//LandH//FAQ Bot//Files.xlsx")
data = loader.load()
texts = [doc.page_content for doc in data]

# ---- Embeddings ----
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# ---- Vector Store ----
vector_path = "L&H-FAQ-POC-1"

# Create vector DB only once
if not os.path.exists(vector_path):
    vector_db = FAISS.from_texts(texts, embedding_model)
    vector_db.save_local(vector_path)

db = FAISS.load_local(vector_path, embedding_model, allow_dangerous_deserialization=True)
retriever = db.as_retriever(search_kwargs={"k": 3})

# ---- Prompt ----
prompt_template = PromptTemplate(
    template="""
You are an intelligent FAQ assistant.
Rules:
1. Use ONLY the information in the context.
2. If context is irrelevant or empty, answer:
   "I don't know. Please wait for the Human reply."
3. Never guess or hallucinate.

Context:
{context}

User Question:
{question}

Answer:
""",
    input_variables=['context', 'question']
)

chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True,
    input_key='question',
    chain_type="stuff",
    chain_type_kwargs={"prompt": prompt_template}
)


def ask_bot(query):
    """Main RAG function for Flask app"""
    response = chain({"question": query})
    answer = response["result"]
    sources = response["source_documents"]

    context_text = " ".join([s.page_content for s in sources]).strip()

    # IDK detection
    if context_text == "" or len(context_text) < 10:
        return "I don't know. Please wait for the Human reply."

    hallucination_phrases = ["i am not sure", "cannot answer", "as an ai", "no information"]
    if any(x in answer.lower() for x in hallucination_phrases):
        return "I don't know. Please wait for the Human reply."

    return answer
