import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

chain = None

def initialize_rag():
    global chain
    if chain is not None:
        return True
    
    try:
        print("=" * 50)
        print("🔧 RAG Initialization Starting...")
        
        load_dotenv()
        gemini_key = os.getenv("gemini_key")
        
        if not gemini_key:
            print("❌ No API key found!")
            return False
        
        print("✓ API key loaded")
        
        # LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_key,
            temperature=0.3
        )
        print("✓ LLM ready")
        
        # Excel
        excel_path = "Files.xlsx"
        if not os.path.exists(excel_path):
            print(f"❌ File not found: {excel_path}")
            print(f"Available files: {os.listdir('.')}")
            return False
        
        print(f"✓ Found {excel_path}")
        
        loader = UnstructuredExcelLoader(excel_path, mode="elements")
        docs = loader.load()
        texts = [d.page_content for d in docs if d.page_content.strip()]
        
        print(f"✓ Loaded {len(texts)} docs")
        
        # Embeddings
        print("⏳ Loading embeddings...")
        embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        print("✓ Embeddings ready")
        
        # FAISS
        vector_path = "faiss_index"
        if not os.path.exists(vector_path):
            print("⏳ Creating FAISS index...")
            db = FAISS.from_texts(texts, embedding_model)
            db.save_local(vector_path)
            print("✓ Index created")
        else:
            print("⏳ Loading FAISS index...")
            db = FAISS.load_local(vector_path, embedding_model, allow_dangerous_deserialization=True)
            print("✓ Index loaded")
        
        retriever = db.as_retriever(search_kwargs={"k": 3})
        
        # Chain
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are a helpful FAQ assistant for Life & Half.
Answer based ONLY on the context below. If unsure, say "I don't know."

Context: {context}

Question: {question}

Answer:"""
        )
        
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        
        print("✅ RAG initialized!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def ask_bot(query):
    if not initialize_rag():
        return "I'm currently unavailable. Please try again later."
    
    try:
        response = chain({"query": query})
        answer = response["result"]
        context = " ".join([d.page_content for d in response.get("source_documents", [])]).strip()
        
        if not context or len(context) < 10:
            return "I don't know. Please wait for the Human reply."
        
        if any(phrase in answer.lower() for phrase in ["i don't know", "not sure", "cannot"]):
            return "I don't know. Please wait for the Human reply."
        
        return answer
        
    except Exception as e:
        print(f"❌ Query error: {e}")
        return "Sorry, I encountered an error. Please try again."

