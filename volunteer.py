from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from app import db
from models import User, Task, Assignment

volunteer_bp = Blueprint('volunteer', __name__)

def volunteer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'volunteer':
            flash('Access denied. Volunteers only.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


@volunteer_bp.route('/dashboard')
@login_required
@volunteer_required
def dashboard():
    my_assignments = Assignment.query.filter_by(user_id=current_user.id).all()

    pending   = [a for a in my_assignments if a.status == 'pending']
    accepted  = [a for a in my_assignments if a.status == 'accepted']
    completed = [a for a in my_assignments if a.status == 'completed']
    declined  = [a for a in my_assignments if a.status == 'declined']

    # Open tasks not yet assigned to this volunteer
    assigned_task_ids = {a.task_id for a in my_assignments}
    open_tasks = Task.query.filter_by(status='open').all()
    suggested  = [t for t in open_tasks if t.id not in assigned_task_ids]

    # Smart-suggest: tasks whose required skills overlap with volunteer's skills
    my_skills = set(current_user.get_skills())
    def skill_overlap(task):
        return len(my_skills.intersection(set(task.get_required_skills())))

    suggested.sort(key=skill_overlap, reverse=True)
    suggested = suggested[:4]

    # Pre-compute score + matching skills for each suggested task (avoid Jinja set-in-loop bug)
    suggested_data = []
    for task in suggested:
        req = set(task.get_required_skills())
        overlap = my_skills.intersection(req)
        score = round((len(overlap) / len(req)) * 100) if req else 0
        suggested_data.append({
            'task': task,
            'score': score,
            'overlap': list(overlap),
            'req': list(req),
        })

    return render_template('volunteer/dashboard.html',
        pending=pending,
        accepted=accepted,
        completed=completed,
        declined=declined,
        suggested_data=suggested_data,
        my_skills=my_skills,
    )


@volunteer_bp.route('/assignments')
@login_required
@volunteer_required
def my_assignments():
    status_filter = request.args.get('status', 'all')
    query = Assignment.query.filter_by(user_id=current_user.id)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    assignments = query.order_by(Assignment.assigned_at.desc()).all()

    counts = {
        'all':       Assignment.query.filter_by(user_id=current_user.id).count(),
        'pending':   Assignment.query.filter_by(user_id=current_user.id, status='pending').count(),
        'accepted':  Assignment.query.filter_by(user_id=current_user.id, status='accepted').count(),
        'completed': Assignment.query.filter_by(user_id=current_user.id, status='completed').count(),
        'declined':  Assignment.query.filter_by(user_id=current_user.id, status='declined').count(),
    }

    return render_template('volunteer/my_assignments.html',
        assignments=assignments,
        status_filter=status_filter,
        counts=counts,
    )


@volunteer_bp.route('/assignments/<int:assignment_id>/respond', methods=['POST'])
@login_required
@volunteer_required
def respond_assignment(assignment_id):
    a = Assignment.query.get_or_404(assignment_id)

    if a.user_id != current_user.id:
        flash('Not authorized.', 'error')
        return redirect(url_for('volunteer.my_assignments'))

    action = request.form.get('action')
    if action == 'accept':
        a.status = 'accepted'
        flash(f'You accepted the task: "{a.task.title}". Thank you!', 'success')
    elif action == 'decline':
        a.status = 'declined'
        flash(f'You declined the task: "{a.task.title}".', 'info')

    db.session.commit()
    return redirect(url_for('volunteer.my_assignments'))


@volunteer_bp.route('/tasks')
@login_required
@volunteer_required
def browse_tasks():
    search = request.args.get('search', '').strip().lower()
    skill_filter = request.args.get('skill', '').strip().lower()

    # Get all open tasks
    tasks = Task.query.filter_by(status='open').order_by(Task.created_at.desc()).all()

    # Apply search
    if search:
        tasks = [t for t in tasks if
                 search in t.title.lower() or
                 (t.description and search in t.description.lower()) or
                 search in (t.required_skills or '').lower()]

    # Apply skill filter
    if skill_filter:
        tasks = [t for t in tasks if skill_filter in (t.required_skills or '').lower()]

    # Score each task by match with volunteer's skills
    my_skills = set(current_user.get_skills())
    assigned_task_ids = {
        a.task_id for a in Assignment.query.filter_by(user_id=current_user.id).all()
    }

    task_data = []
    for t in tasks:
        req = set(t.get_required_skills())
        overlap = my_skills.intersection(req)
        score = round((len(overlap) / len(req)) * 100) if req else 0
        task_data.append({
            'task':    t,
            'score':   score,
            'overlap': overlap,
            'assigned': t.id in assigned_task_ids,
        })

    # Sort by match score descending
    task_data.sort(key=lambda x: x['score'], reverse=True)

    # Collect all unique skills across tasks for filter chips
    all_skills = set()
    for t in Task.query.filter_by(status='open').all():
        all_skills.update(t.get_required_skills())

    return render_template('volunteer/browse_tasks.html',
        task_data=task_data,
        search=search,
        skill_filter=skill_filter,
        all_skills=sorted(all_skills),
    )


@volunteer_bp.route('/tasks/<int:task_id>/apply', methods=['POST'])
@login_required
@volunteer_required
def apply_task(task_id):
    task = Task.query.get_or_404(task_id)

    existing = Assignment.query.filter_by(
        user_id=current_user.id, task_id=task_id
    ).first()

    if existing:
        flash('You have already applied for this task.', 'warning')
        return redirect(url_for('volunteer.browse_tasks'))

    if task.is_full():
        flash('Sorry, this task is already full.', 'warning')
        return redirect(url_for('volunteer.browse_tasks'))

    # Calculate match score
    my_skills  = set(current_user.get_skills())
    req_skills = set(task.get_required_skills())
    score = round((len(my_skills.intersection(req_skills)) / len(req_skills)) * 100) if req_skills else 0

    assignment = Assignment(
        user_id=current_user.id,
        task_id=task_id,
        status='pending',
        match_score=score,
    )
    db.session.add(assignment)
    db.session.commit()

    flash(f'Applied for "{task.title}"! Waiting for coordinator confirmation.', 'success')
    return redirect(url_for('volunteer.my_assignments'))


@volunteer_bp.route('/profile')
@login_required
@volunteer_required
def profile():
    stats = {
        'completed': current_user.completed_tasks_count(),
        'active':    current_user.active_tasks_count(),
        'hours':     current_user.impact_hours(),
        'total':     Assignment.query.filter_by(user_id=current_user.id).count(),
    }
    return render_template('volunteer/profile.html', stats=stats)


@volunteer_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@volunteer_required
def edit_profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.bio  = request.form.get('bio', '').strip()

        skills = request.form.get('skills', '').strip()
        current_user.skills = skills

        # Availability from checkboxes
        slots = request.form.getlist('avail_slots')
        avail_hidden = request.form.get('availability', '')
        current_user.availability = avail_hidden if avail_hidden else ','.join(slots)

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('volunteer.profile'))

    return render_template('volunteer/edit_profile.html')
