"""
Smart matching engine for VolunteerIQ.

Scoring breakdown (total 100 pts):
  - Skill overlap          : 50 pts  (core signal)
  - Availability overlap   : 20 pts
  - Workload balance       : 20 pts  (favour less-busy volunteers)
  - Past completion rate   : 10 pts  (reliability signal)
"""

from models import User, Task, Assignment


# ── helpers ──────────────────────────────────────────────────────────────────

def _skill_score(volunteer_skills: set, required_skills: set) -> float:
    """0-50: proportion of required skills the volunteer covers."""
    if not required_skills:
        return 25.0          # no requirements → neutral score
    overlap = volunteer_skills.intersection(required_skills)
    return round((len(overlap) / len(required_skills)) * 50, 2)


def _availability_score(volunteer_avail: set, task_time_slot: str) -> float:
    """
    0-20: naive keyword match between task time slot string and
    volunteer availability slots.
    E.g. task 'Saturday 10am-2pm' matches 'Sat All Day'.
    """
    if not task_time_slot or not volunteer_avail:
        return 10.0          # unknown → neutral

    slot_lower = task_time_slot.lower()
    keywords = {
        'mon': 'mon', 'tue': 'tue', 'wed': 'wed',
        'thu': 'thu', 'fri': 'fri',
        'sat': 'sat', 'sun': 'sun',
        'morning': 'morning', 'evening': 'evening',
        'afternoon': 'morning',   # map afternoon → morning bucket
        'all day': 'all day', 'weekend': 'sat',
    }

    # Build a set of day/time tokens from the task slot
    task_tokens = set()
    for kw, canonical in keywords.items():
        if kw in slot_lower:
            task_tokens.add(canonical)

    if not task_tokens:
        return 10.0          # can't parse → neutral

    # Check how many of the volunteer's availability slots match
    matched = 0
    for avail in volunteer_avail:
        avail_lower = avail.lower()
        if any(tok in avail_lower for tok in task_tokens):
            matched += 1

    # At least one slot matched → full points; partial → half
    if matched >= 2:
        return 20.0
    elif matched == 1:
        return 14.0
    return 0.0


def _workload_score(volunteer_id: int) -> float:
    """
    0-20: volunteers with fewer active assignments score higher.
    Encourages even distribution.
    """
    active = Assignment.query.filter(
        Assignment.user_id == volunteer_id,
        Assignment.status.in_(['pending', 'accepted'])
    ).count()

    if active == 0:
        return 20.0
    elif active == 1:
        return 16.0
    elif active == 2:
        return 11.0
    elif active == 3:
        return 6.0
    else:
        return 2.0           # very busy — de-prioritise


def _reliability_score(volunteer_id: int) -> float:
    """
    0-10: ratio of completed vs declined assignments.
    New volunteers get a neutral score.
    """
    total = Assignment.query.filter_by(user_id=volunteer_id).count()
    if total == 0:
        return 7.0           # new volunteer → slightly positive prior

    completed = Assignment.query.filter_by(
        user_id=volunteer_id, status='completed'
    ).count()
    declined = Assignment.query.filter_by(
        user_id=volunteer_id, status='declined'
    ).count()

    # Penalise declines, reward completions
    score = ((completed * 1.0) - (declined * 0.5)) / total * 10
    return max(0.0, min(10.0, round(score, 2)))


# ── public API ────────────────────────────────────────────────────────────────

def score_volunteer(volunteer: 'User', task: 'Task') -> dict:
    """
    Return a full scoring breakdown for one volunteer against one task.
    """
    v_skills = set(volunteer.get_skills())
    r_skills = set(task.get_required_skills())
    v_avail  = set(volunteer.get_availability())

    skill_pts   = _skill_score(v_skills, r_skills)
    avail_pts   = _availability_score(v_avail, task.time_slot or '')
    workload_pts= _workload_score(volunteer.id)
    reliability_pts = _reliability_score(volunteer.id)

    total = skill_pts + avail_pts + workload_pts + reliability_pts

    matching_skills = list(v_skills.intersection(r_skills))
    missing_skills  = list(r_skills - v_skills)

    active_tasks = Assignment.query.filter(
        Assignment.user_id == volunteer.id,
        Assignment.status.in_(['pending', 'accepted'])
    ).count()

    return {
        'volunteer':        volunteer,
        'total':            round(total, 1),
        'skill_pts':        skill_pts,
        'avail_pts':        avail_pts,
        'workload_pts':     workload_pts,
        'reliability_pts':  reliability_pts,
        'matching_skills':  matching_skills,
        'missing_skills':   missing_skills,
        'active_tasks':     active_tasks,
        'skill_pct':        round((skill_pts / 50) * 100) if r_skills else 100,
    }


def match_volunteers_to_task(task: 'Task', min_score: float = 0.0) -> list:
    """
    Score all volunteers against a task.
    Returns list of score dicts sorted by total descending.
    Only includes volunteers not already assigned to this task.
    """
    # Get IDs already assigned
    assigned_ids = {
        a.user_id for a in Assignment.query.filter_by(task_id=task.id).all()
    }

    volunteers = User.query.filter_by(role='volunteer').all()
    results = []

    for v in volunteers:
        if v.id in assigned_ids:
            continue
        score = score_volunteer(v, task)
        if score['total'] >= min_score:
            results.append(score)

    results.sort(key=lambda x: x['total'], reverse=True)
    return results


def get_tier(total_score: float) -> tuple:
    """Return (label, css_class, emoji) for a score."""
    if total_score >= 75:
        return ('Excellent', 'score-high',   '🟢')
    elif total_score >= 50:
        return ('Good',      'score-medium', '🟡')
    elif total_score >= 25:
        return ('Fair',      'score-low',    '🟠')
    else:
        return ('Low',       'score-low',    '🔴')
