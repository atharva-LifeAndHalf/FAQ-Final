from flask import Flask, render_template, request, jsonify
import time
import random
import os

# Create Flask app FIRST
app = Flask(__name__)

# Global variables
conversation = []
last_time = time.time()
TIMEOUT = 300
rag_initialized = False

def reset_if_inactive():
    global conversation, last_time
    if time.time() - last_time > TIMEOUT:
        conversation = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/ask", methods=["POST"])
def ask():
    global conversation, last_time, rag_initialized
    
    reset_if_inactive()
    user_msg = request.form.get("message", "").strip()
    
    if not user_msg:
        return jsonify({"reply": "Please enter a message."}), 400
    
    last_time = time.time()
    conversation.append({"role": "user", "text": user_msg})
    
    # Greetings
    if user_msg.lower() in ["hi", "hello", "hey", "yo", "hola"]:
        bot_reply = random.choice([
            "Hello! How can I assist you today?",
            "Hi there! 😊 What can I help you with?",
            "Hey! Ask me anything."
        ])
        conversation.append({"role": "bot", "text": bot_reply})
        return jsonify({"reply": bot_reply})
    
    # Short responses
    if user_msg.lower() in ["ok", "okay", "k", "thanks", "thank you"]:
        bot_reply = random.choice(["You're welcome! 😊", "Glad I could help!", "Anytime!"])
        conversation.append({"role": "bot", "text": bot_reply})
        return jsonify({"reply": bot_reply})
    
    # RAG response
    try:
        # Lazy import - only load when needed
        if not rag_initialized:
            print("🔄 First query - initializing RAG...")
            from rag_engine import ask_bot
            globals()['ask_bot'] = ask_bot
            rag_initialized = True
        
        bot_raw = ask_bot(user_msg)
        
        if "don't know" in bot_raw.lower():
            final = bot_raw
        else:
            final = bot_raw + random.choice(["", " Let me know if you want to know more!", " Happy to help!"])
        
        conversation.append({"role": "bot", "text": final})
        return jsonify({"reply": final})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        error_msg = "Sorry, I'm having trouble. Please try again!"
        conversation.append({"role": "bot", "text": error_msg})
        return jsonify({"reply": error_msg})

# This block should NOT run on Gunicorn
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
