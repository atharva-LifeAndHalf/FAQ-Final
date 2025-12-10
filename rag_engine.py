import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import openpyxl
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Global variables
faq_data = []
vectorizer = None
tfidf_matrix = None
genai_model = None

def initialize_rag():
    global faq_data, vectorizer, tfidf_matrix, genai_model
    
    if genai_model is not None:
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
        
        # Initialize Gemini
        genai.configure(api_key=gemini_key)
        genai_model = genai.GenerativeModel('gemini-2.5-flash')
        print("✓ Gemini initialized")
        
        # Load Excel
        excel_path = "Files.xlsx"
        if not os.path.exists(excel_path):
            print(f"❌ File not found: {excel_path}")
            return False
        
        print(f"✓ Found {excel_path}")
        
        # Read Excel with openpyxl (lightweight)
        wb = openpyxl.load_workbook(excel_path, read_only=True)
        sheet = wb.active
        
        # Extract all text from Excel
        for row in sheet.iter_rows(values_only=True):
            row_text = " ".join([str(cell) for cell in row if cell])
            if row_text.strip():
                faq_data.append(row_text.strip())
        
        wb.close()
        print(f"✓ Loaded {len(faq_data)} rows")
        
        # Create TF-IDF vectors (lightweight alternative to embeddings)
        print("⏳ Creating TF-IDF vectors...")
        vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(faq_data)
        print("✓ Vectors created")
        
        print("✅ RAG initialized!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def find_relevant_context(query, top_k=3):
    """Find most relevant FAQ entries using TF-IDF similarity"""
    try:
        query_vec = vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        relevant_docs = [faq_data[i] for i in top_indices if similarities[i] > 0.1]
        return "\n\n".join(relevant_docs) if relevant_docs else ""
        
    except Exception as e:
        print(f"❌ Context retrieval error: {e}")
        return ""


def ask_bot(query):
    if not initialize_rag():
        return "I'm currently unavailable. Please try again later."
    
    try:
        # Find relevant context
        context = find_relevant_context(query)
        
        if not context or len(context) < 20:
            return "I don't know. Please wait for the Human reply."
        
        # Create prompt
        prompt = f"""You are a helpful FAQ assistant for Life & Half.
Answer the question based ONLY on the context below. If the answer is not in the context, say "I don't know."

Context:
{context}

Question: {query}

Answer:"""
        
        # Get response from Gemini
        response = genai_model.generate_content(prompt)
        answer = response.text.strip()
        
        # Check for uncertain answers
        if any(phrase in answer.lower() for phrase in ["i don't know", "not sure", "cannot", "no information"]):
            return "I don't know. Please wait for the Human reply."
        
        return answer
        
    except Exception as e:
        print(f"❌ Query error: {e}")
        import traceback
        traceback.print_exc()
        return "Sorry, I encountered an error. Please try again."

