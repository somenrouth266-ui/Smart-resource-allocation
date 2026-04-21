import os, json, time
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from functools import wraps
from models import User, Task, Assignment
from matching import match_volunteers_to_task, score_volunteer
import urllib.request
import urllib.error

ai_bp = Blueprint('ai', __name__)

# --- 1. DECORATOR DEFINITION (Must be at the top) ---
def coordinator_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'coordinator':
            return jsonify({'error': 'Coordinators only'}), 403
        return f(*args, **kwargs)
    return decorated

# --- 2. HELPER FUNCTIONS ---
def _build_prompt(task: Task, matches: list) -> str:
    top = matches[:5]
    candidates = []
    for i, m in enumerate(top, 1):
        v = m['volunteer']
        candidates.append(
            f"{i}. {v.name} (score {m['total']}/100)\n"
            f"   Skills matched: {', '.join(m['matching_skills']) or 'none'}\n"
            f"   Skills missing: {', '.join(m['missing_skills']) or 'none'}\n"
            f"   Active tasks: {m['active_tasks']}\n"
            f"   Availability slots: {', '.join(v.get_availability()) or 'not specified'}"
        )
    candidates_text = "\n".join(candidates)
    prompt = f"""You are a volunteer coordination assistant helping a coordinator choose the best volunteer for a task.

TASK DETAILS:
- Title: {task.title}
- Description: {task.description or 'Not provided'}
- Required skills: {', '.join(task.get_required_skills()) or 'none specified'}
- Time slot: {task.time_slot or 'not specified'}
- Location: {task.location or 'not specified'}
- Priority: {task.priority}

TOP CANDIDATES:
{candidates_text}

Please provide:
1. Your top pick (name only) and a 2-sentence explanation.
2. A brief note on a second choice.
3. One practical tip for the coordinator.

Keep it concise and actionable."""
    return prompt

def _smart_fallback(task: Task, matches: list) -> str:
    top = matches[0]
    top_vol = top['volunteer']
    return (
        f"**Top pick: {top_vol.name}**\n\n"
        f"Based on our local matching algorithm, {top_vol.name} is the strongest fit for **{task.title}** "
        f"due to their matching skills and current availability."
    )

# --- 3. THE ROUTE ---
@ai_bp.route('/suggest/<int:task_id>', methods=['POST'])
@login_required
@coordinator_required
def suggest(task_id):
    task = Task.query.get_or_404(task_id)
    matches = match_volunteers_to_task(task)
    if not matches:
        return jsonify({'error': 'No candidates available.'}), 400

    api_key = os.getenv('GEMINI_API_KEY', '')
    
    if not api_key:
        return jsonify({'suggestion': _smart_fallback(task, matches), 'mock': True})

    prompt = _build_prompt(task, matches)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 400, "temperature": 0.7}
    }).encode('utf-8')

    for attempt in range(2):
        try:
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                if 'candidates' in data and data['candidates']:
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    return jsonify({'suggestion': text.strip(), 'mock': False})
                raise Exception("AI Response structure invalid")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(2)
                continue
            break # Exit loop and use fallback
        except Exception:
            break

    return jsonify({'suggestion': _smart_fallback(task, matches), 'mock': True})
