import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA

# Global variable to store initialized chain
chain = None
initialization_error = None

def initialize_rag():
    """Initialize RAG components on first use"""
    global chain, initialization_error
    
    # Already initialized
    if chain is not None:
        return True
    
    # Previous initialization failed
    if initialization_error is not None:
        return False
    
    try:
        print("=" * 50)
        print("🔧 Starting RAG Engine Initialization...")
        print("=" * 50)
        
        # Load environment variables
        load_dotenv()
        gemini_key = os.getenv("gemini_key")
        
        if not gemini_key:
            raise ValueError("❌ gemini_key not found in environment variables!")
        
        print("✓ API key loaded successfully")
        
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",  # Use stable model
            google_api_key=gemini_key,
            temperature=0.3
        )
        print("✓ LLM initialized")
        
        # Load Excel file
        excel_path = "faq.xlsx"
        
        # Check if file exists
        if not os.path.exists(excel_path):
            print(f"❌ Excel file not found at: {excel_path}")
            print(f"Current directory: {os.getcwd()}")
            print(f"Files in directory: {os.listdir('.')}")
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        print(f"✓ Excel file found: {excel_path}")
        
        loader = UnstructuredExcelLoader(excel_path)
        docs = loader.load()
        
        if not docs:
            raise ValueError("No documents loaded from Excel file!")
        
        texts = [d.page_content for d in docs if d.page_content.strip()]
        
        if not texts:
            raise ValueError("No valid text content found in Excel file!")
        
        print(f"✓ Loaded {len(texts)} documents from Excel")
        
        # Initialize embeddings
        print("⏳ Loading embedding model (this may take a minute)...")
        embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        print("✓ Embedding model loaded")
        
        # Create or load vector database
        vector_path = "faiss_index"
        
        if not os.path.exists(vector_path):
            print("⏳ Creating FAISS index (first time setup)...")
            db = FAISS.from_texts(texts, embedding_model)
            db.save_local(vector_path)
            print("✓ FAISS index created and saved")
        else:
            print("⏳ Loading existing FAISS index...")
            db = FAISS.load_local(
                vector_path, 
                embedding_model, 
                allow_dangerous_deserialization=True
            )
            print("✓ FAISS index loaded from disk")
        
        # Create retriever
        retriever = db.as_retriever(search_kwargs={"k": 3})
        print("✓ Retriever configured")
        
        # Create prompt template
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are an intelligent FAQ assistant for Life & Half.
Use ONLY the context provided below to answer the question. Do not make up information.
If the answer is not in the context, say "I don't know."

Context:
{context}

User Question:
{question}

Answer:"""
        )
        
        # Create QA chain
        chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": prompt}
        )
        
        print("✅ RAG Engine initialized successfully!")
        print("=" * 50)
        return True
        
    except Exception as e:
        initialization_error = str(e)
        print("=" * 50)
        print(f"❌ RAG Engine initialization FAILED!")
        print(f"Error: {e}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        return False


def ask_bot(query):
    """
    Query the RAG system
    Returns: Answer string
    """
    # Initialize on first use
    if not initialize_rag():
        return "I'm currently unavailable. Please try again later or wait for human assistance."
    
    try:
        # Query the chain
        response = chain({"query": query})
        answer = response["result"]
        source_docs = response.get("source_documents", [])
        
        # Extract context
        context = " ".join([d.page_content for d in source_docs]).strip()
        
        # Check if we have valid context
        if not context or len(context) < 10:
            return "I don't know. Please wait for the Human reply."
        
        # Check for uncertain answers
        bad_phrases = [
            "i don't know", 
            "not sure", 
            "cannot", 
            "no information",
            "i do not know",
            "i'm not sure"
        ]
        
        answer_lower = answer.lower()
        if any(phrase in answer_lower for phrase in bad_phrases):
            return "I don't know. Please wait for the Human reply."
        
        return answer
        
    except Exception as e:
        print(f"❌ Error in ask_bot: {e}")
        import traceback
        traceback.print_exc()
        return "Sorry, I encountered an error. Please try again or wait for human assistance."
