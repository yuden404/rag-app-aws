"""
Flask API for the South Park RAG application (AWS-native version).
Routes:
  GET  /         → serves the UI
  GET  /health   → health-check
  POST /api/ask  → RAG question-answering
"""

import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from bedrock_utils import retrieve_from_kb, claude_chat

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

app = Flask(
    __name__,
    template_folder=SCRIPT_DIR,
    static_folder=SCRIPT_DIR,
    static_url_path="",
)


# --- Hebrew helpers ---

def is_hebrew(text: str) -> bool:
    return any("\u0590" <= ch <= "\u05FF" for ch in text)


def translate_to_english(text: str) -> str:
    """Use Claude to translate Hebrew → English for retrieval."""
    if not is_hebrew(text):
        return text
    return claude_chat(
        prompt=f"Translate the following text to English. Return ONLY the translated text.\n\nText: {text}",
        max_tokens=256,
    )


# --- RAG pipeline ---

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about the TV show South Park. "
    "Use ONLY the provided context to answer. If the context does not contain enough "
    "information, say so honestly. Do not make up information."
)


def build_rag_prompt(question: str, sources: list[dict]) -> str:
    if not sources:
        if is_hebrew(question):
            return "אין לי מספיק מידע בבסיס הידע שלי כדי לענות על שאלה זו על סאות' פארק."
        return "I don't have enough information in my knowledge base to answer this question about South Park."

    context = "\n\n".join(s["text"] for s in sources)
    lang = "Answer in Hebrew. Character names can stay in English." if is_hebrew(question) else "Answer in English."
    return f"""{lang}

Context:
{context}

Question: {question}

Answer:"""


# --- Routes ---

@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/ask")
def api_ask():
    data = request.get_json(silent=True)
    if not data or not data.get("question", "").strip():
        return jsonify({"answer": None, "sources": [], "error": "Please enter a question."}), 400

    question = data["question"].strip()

    try:
        english_query = translate_to_english(question)
        sources = retrieve_from_kb(english_query, k=5)
        prompt = build_rag_prompt(question, sources)

        if isinstance(prompt, str) and not sources:
            return jsonify({"answer": prompt, "sources": [], "error": None})

        answer = claude_chat(prompt=prompt, system=SYSTEM_PROMPT)
        return jsonify({"answer": answer, "sources": sources, "error": None})

    except Exception as e:
        error_msg = str(e)
        print(f"Error processing question: {error_msg}")
        if "ThrottlingException" in error_msg or "Too many requests" in error_msg:
            user_error = "API rate limit exceeded. Please try again in a minute."
        else:
            user_error = "Something went wrong. Please try again."
        return jsonify({"answer": None, "sources": [], "error": user_error}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
