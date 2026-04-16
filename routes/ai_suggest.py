import os, json
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from functools import wraps
from models import User, Task, Assignment
from matching import match_volunteers_to_task, score_volunteer

ai_bp = Blueprint('ai', __name__)

def coordinator_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'coordinator':
            return jsonify({'error': 'Coordinators only'}), 403
        return f(*args, **kwargs)
    return decorated


def _build_prompt(task: Task, matches: list) -> str:
    """Build the prompt sent to Claude."""
    top = matches[:5]  # only top 5 to stay within context

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
- Volunteers still needed: {task.volunteers_needed - task.accepted_volunteers_count()}

TOP CANDIDATES (ranked by smart matching algorithm):
{candidates_text}

Please provide:
1. Your top pick (name only) and a 2-sentence explanation of why they are the best fit.
2. A brief note on your second choice if the first is unavailable.
3. One practical tip for the coordinator about this task or volunteer match.

Keep your response concise (under 150 words), friendly, and actionable. 
Do NOT repeat the scores — focus on qualitative reasoning."""

    return prompt


@ai_bp.route('/suggest/<int:task_id>', methods=['POST'])
@login_required
@coordinator_required
def suggest(task_id):
    task = Task.query.get_or_404(task_id)
    matches = match_volunteers_to_task(task)

    if not matches:
        return jsonify({
            'error': 'No candidates available to suggest from.'
        }), 400

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        # Return a helpful mock response if no API key set
        top = matches[0]['volunteer']
        return jsonify({
            'suggestion': (
                f"**Top pick: {top.name}**\n\n"
                f"Based on the matching algorithm, {top.name} scored highest with "
                f"{len(matches[0]['matching_skills'])} matching skill(s): "
                f"{', '.join(matches[0]['matching_skills']) or 'general fit'}. "
                f"They currently have {matches[0]['active_tasks']} active task(s), "
                f"making them a good fit for this assignment.\n\n"
                f"*Set your ANTHROPIC_API_KEY environment variable to get full AI-powered suggestions.*"
            ),
            'mock': True
        })

    prompt = _build_prompt(task, matches)

    try:
        import urllib.request
        payload = json.dumps({
            'model': 'claude-sonnet-4-20250514',
            'max_tokens': 300,
            'messages': [{'role': 'user', 'content': prompt}]
        }).encode('utf-8')

        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            text = data['content'][0]['text']

        return jsonify({'suggestion': text, 'mock': False})

    except Exception as e:
        return jsonify({'error': f'AI request failed: {str(e)}'}), 500
