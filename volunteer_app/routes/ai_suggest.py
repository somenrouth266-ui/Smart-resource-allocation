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


def _smart_fallback(task: Task, matches: list) -> str:
    top     = matches[0]
    second  = matches[1] if len(matches) > 1 else None
    top_vol = top['volunteer']

    skills_text = ', '.join(top['matching_skills']) if top['matching_skills'] \
                  else 'a general aptitude for this type of work'
    workload    = "no current active tasks, making them immediately available" \
                  if top['active_tasks'] == 0 \
                  else f"a manageable workload of {top['active_tasks']} active task(s)"

    second_line = ""
    if second:
        s = second['volunteer']
        second_line = (
            f"\n\n**If {top_vol.name} is unavailable**, {s.name} is a solid alternative — "
            f"they bring {'complementary skills' if second['matching_skills'] else 'enthusiasm and availability'} "
            f"and currently have {second['active_tasks']} active task(s)."
        )

    priority_tip = {
        'high':   f"Given the high priority of this task, I'd recommend reaching out to "
                  f"{top_vol.name} directly to confirm availability before formally assigning.",
        'medium': f"This is a good opportunity to assign {top_vol.name} early so they have time to prepare.",
        'low':    f"Since priority is low, you have flexibility — confirm {top_vol.name}'s preference before assigning."
    }.get(task.priority, f"Reach out to {top_vol.name} to confirm they're ready to take this on.")

    return (
        f"**Top pick: {top_vol.name}**\n\n"
        f"After reviewing all candidates against the requirements for **{task.title}**, "
        f"{top_vol.name} stands out as the strongest match. "
        f"They bring {skills_text} and have {workload}."
        f"{second_line}\n\n"
        f"**Coordinator tip:** {priority_tip}"
    )


@ai_bp.route('/suggest/<int:task_id>', methods=['POST'])
@login_required
@coordinator_required
def suggest(task_id):
    task = Task.query.get_or_404(task_id)
    matches = match_volunteers_to_task(task)
    if not matches:
        return jsonify({'error': 'No candidates available to suggest from.'}), 400

    # 1. Update to the Gemini Key
    api_key = os.getenv('GEMINI_API_KEY', '')
    if not api_key:
        return jsonify({
            'suggestion': _smart_fallback(task, matches),
            'mock': False
        })

    prompt = _build_prompt(task, matches)
    try:
        import urllib.request

        # 2. Update to Gemini Endpoint (using 2.0 Flash for speed/low cost)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        # 3. Update JSON Payload Structure
        payload = json.dumps({
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 1024,
                "temperature": 0.7
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            # 4. Update response parsing for Gemini's structure
            text = data['candidates'][0]['content']['parts'][0]['text']

        return jsonify({'suggestion': text, 'mock': False})
    except Exception as e:
        return jsonify({'error': f'Gemini request failed: {str(e)}'}), 500
