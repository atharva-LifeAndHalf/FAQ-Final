from flask import Flask, render_template, request, jsonify
import time
import random
import os

app = Flask(__name__)

# Import ask_bot but don't initialize yet (lazy loading)
from rag_engine import ask_bot

# Global conversation state
conversation = []
last_time = time.time()
TIMEOUT = 300  # 5 minutes

def reset_if_inactive():
    """Reset conversation after timeout"""
    global conversation, last_time
    time_diff = time.time() - last_time
    if time_diff > TIMEOUT:
        conversation = []
        print(f"🔄 Conversation reset after {time_diff:.0f}s of inactivity")

@app.route("/")
def index():
    """Render main chat interface"""
    return render_template("index.html")

@app.route("/health")
def health():
    """Health check endpoint for Render"""
    return jsonify({
        "status": "healthy",
        "message": "Flask app is running"
    }), 200

@app.route("/ask", methods=["POST"])
def ask():
    """Handle user questions"""
    global conversation, last_time
    
    try:
        # Reset if inactive
        reset_if_inactive()
        
        # Get user message
        user_msg = request.form.get("message", "").strip()
        
        if not user_msg:
            return jsonify({"reply": "Please enter a message."}), 400
        
        # Update activity time
        last_time = time.time()
        
        # Add to conversation
        conversation.append({"role": "user", "text": user_msg})
        
        print(f"👤 User: {user_msg}")
        
        # Handle greetings
        greetings = ["hi", "hello", "hey", "yo", "hola", "sup", "heya"]
        greet_replies = [
            "Hello! How can I assist you today?",
            "Hi there! 😊 What can I help you with?",
            "Hey! Ask me anything about Life & Half.",
            "Hello! I'm here to help you."
        ]
        
        if user_msg.lower() in greetings:
            bot_reply = random.choice(greet_replies)
            conversation.append({"role": "bot", "text": bot_reply})
            print(f"🤖 Bot: {bot_reply}")
            return jsonify({"reply": bot_reply})
        
        # Handle short acknowledgments
        short_words = ["ok", "okay", "k", "cool", "nice", "thanks", "thank you", "thx", "ty"]
        short_replies = [
            "You're welcome! 😊",
            "Glad I could help!",
            "Anytime!",
            "Happy to assist!",
            "Great! Let me know if you need anything else."
        ]
        
        if user_msg.lower() in short_words:
            bot_reply = random.choice(short_replies)
            conversation.append({"role": "bot", "text": bot_reply})
            print(f"🤖 Bot: {bot_reply}")
            return jsonify({"reply": bot_reply})
        
        # Get RAG response
        print("🔍 Querying RAG engine...")
        bot_raw = ask_bot(user_msg)
        
        # Add personality to response
        endings = [
            "",
            " Let me know if you want to know more!",
            " Feel free to ask if you have more questions!",
            " Happy to help! 😊",
            " Hope that helps!"
        ]
        
        # Don't add endings to "I don't know" responses
        if "don't know" in bot_raw.lower() or "unavailable" in bot_raw.lower():
            final_reply = bot_raw
        else:
            final_reply = bot_raw + random.choice(endings)
        
        conversation.append({"role": "bot", "text": final_reply})
        print(f"🤖 Bot: {final_reply}")
        
        return jsonify({"reply": final_reply})
        
    except Exception as e:
        print(f"❌ Error in /ask endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        error_msg = "Sorry, something went wrong. Please try again!"
        conversation.append({"role": "bot", "text": error_msg})
        return jsonify({"reply": error_msg}), 500

@app.route("/reset", methods=["POST"])
def reset():
    """Reset conversation manually"""
    global conversation
    conversation = []
    return jsonify({"message": "Conversation reset successfully"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

# -------- Start Flask App --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    print("=" * 60)
    print(f"🚀 Starting Flask App on port {port}")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"📂 Files available: {os.listdir('.')}")
    print("=" * 60)
    
    # Run Flask
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False  # Set to False for production
    )
