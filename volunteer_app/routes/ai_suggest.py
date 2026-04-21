import os, json, time
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from functools import wraps
from models import User, Task, Assignment
from matching import match_volunteers_to_task, score_volunteer
import urllib.request
import urllib.error

ai_bp = Blueprint('ai', __name__)

# ... (coordinator_required and _build_prompt stay the same) ...

@ai_bp.route('/suggest/<int:task_id>', methods=['POST'])
@login_required
@coordinator_required
def suggest(task_id):
    task = Task.query.get_or_404(task_id)
    matches = match_volunteers_to_task(task)
    if not matches:
        return jsonify({'error': 'No candidates available to suggest from.'}), 400

    api_key = os.getenv('GEMINI_API_KEY', '')
    
    # Fallback if no API key is found in Railway Variables
    if not api_key:
        return jsonify({
            'suggestion': _smart_fallback(task, matches),
            'mock': True
        })

    prompt = _build_prompt(task, matches)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 400, # Keep it short to save quota
            "temperature": 0.7
        }
    }).encode('utf-8')

    # Try the request with a simple retry for 429 errors
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url, data=payload, 
                headers={'Content-Type': 'application/json'}, 
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                # Safe parsing of Gemini's specific JSON structure
                if 'candidates' in data and data['candidates']:
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    return jsonify({'suggestion': text.strip(), 'mock': False})
                else:
                    raise Exception("Empty response from AI")

        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(2) # Wait 2 seconds and try again once
                continue
            return jsonify({'error': f'Gemini is busy (Error {e.code}). Try again in a minute.'}), e.code
        except Exception as e:
            # If AI fails completely, use your local _smart_fallback logic
            return jsonify({
                'suggestion': _smart_fallback(task, matches),
                'error': str(e),
                'mock': True 
            })

    return jsonify({'suggestion': _smart_fallback(task, matches), 'mock': True})
