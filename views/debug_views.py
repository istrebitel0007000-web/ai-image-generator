from flask import Blueprint, jsonify
import traceback

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/api/v1/debug-gemini')
def debug_gemini():
    from services.image_service import fetch_image_bytes, GEMINI_API_KEY, GEMINI_MODEL
    result = {'api_key_set': bool(GEMINI_API_KEY), 'api_key_length': len(GEMINI_API_KEY) if GEMINI_API_KEY else 0, 'model': GEMINI_MODEL}
    try:
        data = fetch_image_bytes('a cat')
        result['success'] = True
        result['bytes_received'] = len(data)
    except Exception as e:
        result['success'] = False
        result['error_type'] = type(e).__name__
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
    return jsonify(result)
