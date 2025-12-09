# app.py

from flask import Flask, render_template, request, jsonify
from rag_engine import ask_bot
import time
import random

app = Flask(__name__)

conversation_history = []
last_message_time = time.time()

CONVERSATION_TIMEOUT = 30  # seconds


def reset_if_timeout():
    global conversation_history, last_message_time
    if time.time() - last_message_time > CONVERSATION_TIMEOUT:
        conversation_history = []


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    global conversation_history, last_message_time

    reset_if_timeout()

    user_text = request.form["message"].strip().lower()
    last_message_time = time.time()

    conversation_history.append({"role": "user", "text": user_text})

    # -----------------------------
    # GREETING LOGIC
    # -----------------------------
    greeting_words = ["hi", "hii", "hiii", "hello", "hey", "heyy", "yo", "hola", "hey there"]

    greeting_replies = [
        "Hey! How can I help you today? 😊",
        "Hello! What would you like to know?",
        "Hi there! How can I assist you?",
        "Hey! I'm here to help.",
        "Hello! Feel free to ask me anything.",
        "Hi! How can I support you today?",
    ]

    if user_text in greeting_words:
        bot_reply = random.choice(greeting_replies)
        conversation_history.append({"role": "bot", "text": bot_reply})
        return jsonify({"reply": bot_reply})

    # -----------------------------
    # QUICK RESPONSE LOGIC
    # -----------------------------
    quick_words = ["ok", "okay", "k", "okie", "cool", "great", "thanks", "thank you", "nice"]

    quick_replies = [
        "Okay cool 😊",
        "Great! Happy to help!",
        "Awesome!",
        "Perfect!",
        "Glad to help!",
        "Thank you too!",
        "Sure, anytime!",
    ]

    if user_text in quick_words:
        bot_reply = random.choice(quick_replies)
        conversation_history.append({"role": "bot", "text": bot_reply})
        return jsonify({"reply": bot_reply})

    # -----------------------------
    # NORMAL RAG RESPONSE
    # -----------------------------
    bot_raw_reply = ask_bot(user_text)

    # If it's an IDK message, return as is
    if bot_raw_reply.startswith("I don't"):
        final_reply = bot_raw_reply
    else:
        final_reply = bot_raw_reply

    # Add natural endings
    natural_endings = [
        "",
        " Let me know if you want to know more!",
        " Hope this helps!",
        " Feel free to ask anything else!",
        " Happy to explain more if needed!",
    ]

    if not final_reply.startswith("I don't") and len(final_reply) < 200:
        final_reply += random.choice(natural_endings)

    conversation_history.append({"role": "bot", "text": final_reply})
    return jsonify({"reply": final_reply})


if __name__ == "__main__":
    app.run(debug=True)
