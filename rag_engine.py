import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import openpyxl
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Global vars
faq_data = []
vectorizer = None
tfidf_matrix = None
genai_model = None

# General identity/intro responses (NOT FAQ)
GENERAL_RESPONSES = {
    "who are you": "I'm Life & Half’s AI assistant, here to help you with information and support.",
    "what are you": "I'm an AI assistant designed to answer questions related to Life & Half.",
    "what do you do": "I help users by answering questions and providing information about Life & Half.",
    "what can you do": "I can answer your questions, guide you through Life & Half’s services, and help you understand what we offer.",
    "can you help": "Of course! Tell me what you're looking for.",
    "help me": "Sure! What do you need help with?",
    "what is this": "This is Life & Half’s AI assistant — here to guide and support you.",
    "purpose": "My purpose is to help users understand Life & Half and its services.",
    "are you human": "I'm not human. I'm an AI created to help you.",
    "human": "I'm not human — I'm Life & Half’s AI assistant."
}


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
        genai_model = genai.GenerativeModel("gemini-2.5-flash")
        print("✓ Gemini initialized")

        # Load FAQ Excel
        excel_path = "Files.xlsx"
        if not os.path.exists(excel_path):
            print(f"❌ File not found: {excel_path}")
            return False

        print(f"✓ Found {excel_path}")

        wb = openpyxl.load_workbook(excel_path, read_only=True)
        sheet = wb.active

        # Extract rows
        for row in sheet.iter_rows(values_only=True):
            line = " ".join([str(c) for c in row if c])
            if line.strip():
                faq_data.append(line.strip())

        wb.close()
        print(f"✓ Loaded {len(faq_data)} FAQ rows")

        # Vectorize with TF-IDF
        print("⏳ Creating TF-IDF vectors...")
        vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(faq_data)
        print("✓ Vectors created")

        print("✅ RAG initialized!")
        print("=" * 50)

        return True

    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False



def find_relevant_context(query, top_k=3):
    """TF-IDF semantic search"""
    try:
        query_vec = vectorizer.transform([query])
        sims = cosine_similarity(query_vec, tfidf_matrix).flatten()
        top = np.argsort(sims)[-top_k:][::-1]

        relevant = [faq_data[i] for i in top if sims[i] > 0.1]
        return "\n\n".join(relevant) if relevant else ""

    except:
        return ""



def ask_bot(query):
    """Main RAG handler"""
    if not initialize_rag():
        return "I'm currently unavailable. Please try again later."

    # Check General Responses FIRST
    q_lower = query.lower()
    for key in GENERAL_RESPONSES:
        if key in q_lower:
            return GENERAL_RESPONSES[key]

    try:
        context = find_relevant_context(query)

        if not context or len(context) < 20:
            return "I don't know. Please wait for the Human reply."

        # NEW IMPROVED PROMPT
        prompt = f"""
You are Life & Half’s official AI FAQ assistant.

Answer the user’s question based ONLY on the information provided in the context below.

Rules:
- If the context contains the answer in any form (even if phrased differently), answer it clearly.
- Merge multiple lines if needed.
- If the answer is NOT present in the context, reply ONLY with: "I don't know. Please wait for the Human reply."
- No guessing.
- No adding new details.
- Keep the answer clear and correct.

Context:
{context}

Question: {query}

Answer:
"""

        response = genai_model.generate_content(prompt)
        answer = response.text.strip()

        # Check hallucinations
        if "i don't know" in answer.lower():
            return "I don't know. Please wait for the Human reply."

        return answer

    except Exception:
        return "Sorry, I encountered an error. Please try again."
