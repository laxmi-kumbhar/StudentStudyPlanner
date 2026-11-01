from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.utils.auth_helpers import get_current_user_id
from backend.services.ai_service import (
    ask_study_ai,
    get_student_study_context,
    get_ai_config_status,
    save_ai_api_key,
    generate_ai_flashcards
)

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

@ai_bp.route('/ask', methods=['POST'])
def ask():
    user_id = get_current_user_id()
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    history = data.get('history', [])

    if not prompt:
        return jsonify({"success": False, "error": "Prompt cannot be empty"}), 400

    try:
        answer = ask_study_ai(user_id, prompt, history)
        return jsonify({
            "success": True,
            "answer": answer,
            "timestamp": datetime.now().strftime("%H:%M")
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@ai_bp.route('/flashcards', methods=['GET', 'POST'])
def flashcards():
    """Generate high-yield revision flashcards for active recall study."""
    user_id = get_current_user_id()
    if request.method == 'POST':
        data = request.get_json() or {}
    else:
        data = request.args or {}
    topic = data.get('topic', '').strip()
    subject_id = data.get('subject_id')
    try:
        cards = generate_ai_flashcards(user_id, topic=topic, subject_id=subject_id)
        return jsonify({
            "success": True,
            "topic": topic or "Core Revision",
            "cards": cards
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@ai_bp.route('/context', methods=['GET'])
def context():
    user_id = get_current_user_id()
    ctx = get_student_study_context(user_id)
    return jsonify({"success": True, "context": ctx})

@ai_bp.route('/config', methods=['GET'])
def get_config():
    """Retrieve current AI engine status and configured providers."""
    try:
        cfg = get_ai_config_status()
        return jsonify({"success": True, "config": cfg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@ai_bp.route('/config', methods=['POST'])
def save_config():
    """Save user-configured API key (Gemini, Groq, OpenAI) securely to environment & .env."""
    data = request.get_json() or {}
    provider = data.get('provider', '').strip().lower()
    api_key = data.get('api_key', '').strip()

    if not provider:
        return jsonify({"success": False, "error": "Provider is required (gemini, groq, openai, builtin)"}), 400

    try:
        cfg = save_ai_api_key(provider, api_key)
        return jsonify({
            "success": True,
            "message": f"Successfully updated AI provider to {provider.title()}",
            "config": cfg
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
