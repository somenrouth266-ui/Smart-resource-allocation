from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from app import db
from models import User, Task, Assignment
from matching import match_volunteers_to_task, get_tier

coordinator_bp = Blueprint('coordinator', __name__)

def coordinator_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'coordinator':
            flash('Access denied. Coordinators only.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

@coordinator_bp.route('/dashboard')
@login_required
@coordinator_required
def dashboard():
    # Stats
    total_tasks      = Task.query.count()
    open_tasks       = Task.query.filter_by(status='open').count()
    inprogress_tasks = Task.query.filter_by(status='in-progress').count()
    completed_tasks  = Task.query.filter_by(status='completed').count()
    total_volunteers = User.query.filter_by(role='volunteer').count()
    total_assignments = Assignment.query.count()
    pending_assignments = Assignment.query.filter_by(status='pending').count()

    # Recent tasks (latest 5)
    recent_tasks = Task.query.order_by(Task.created_at.desc()).limit(5).all()

    # Recent assignments (latest 5)
    recent_assignments = Assignment.query.order_by(Assignment.assigned_at.desc()).limit(5).all()

    return render_template('coordinator/dashboard.html',
        total_tasks=total_tasks,
        open_tasks=open_tasks,
        inprogress_tasks=inprogress_tasks,
        completed_tasks=completed_tasks,
        total_volunteers=total_volunteers,
        total_assignments=total_assignments,
        pending_assignments=pending_assignments,
        recent_tasks=recent_tasks,
        recent_assignments=recent_assignments,
    )

@coordinator_bp.route('/tasks')
@login_required
@coordinator_required
def tasks():
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')

    query = Task.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)

    all_tasks = query.order_by(Task.created_at.desc()).all()

    return render_template('coordinator/tasks.html',
        tasks=all_tasks,
        status_filter=status_filter,
        priority_filter=priority_filter,
    )

@coordinator_bp.route('/tasks/create', methods=['GET', 'POST'])
@login_required
@coordinator_required
def create_task():
    if request.method == 'POST':
        title           = request.form.get('title', '').strip()
        description     = request.form.get('description', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        time_slot       = request.form.get('time_slot', '').strip()
        location        = request.form.get('location', '').strip()
        priority        = request.form.get('priority', 'medium')
        volunteers_needed = int(request.form.get('volunteers_needed', 1))

        if not title:
            flash('Task title is required.', 'error')
            return render_template('coordinator/create_task.html')

        task = Task(
            title=title,
            description=description,
            required_skills=required_skills,
            time_slot=time_slot,
            location=location,
            priority=priority,
            volunteers_needed=volunteers_needed,
        )
        db.session.add(task)
        db.session.commit()
        flash(f'Task "{title}" created successfully!', 'success')
        return redirect(url_for('coordinator.tasks'))

    return render_template('coordinator/create_task.html')

@coordinator_bp.route('/tasks/<int:task_id>')
@login_required
@coordinator_required
def task_detail(task_id):
    task        = Task.query.get_or_404(task_id)
    assignments = Assignment.query.filter_by(task_id=task_id).all()
    matches     = match_volunteers_to_task(task)

    # Annotate matches with tier info
    for m in matches:
        m['tier'], m['tier_class'], m['tier_emoji'] = get_tier(m['total'])

    return render_template('coordinator/task_detail.html',
        task=task,
        assignments=assignments,
        matches=matches,
    )

@coordinator_bp.route('/tasks/<int:task_id>/status', methods=['POST'])
@login_required
@coordinator_required
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    new_status = request.form.get('status')
    if new_status in ('open', 'in-progress', 'completed'):
        task.status = new_status
        db.session.commit()
        flash(f'Task status updated to "{new_status}".', 'success')
    return redirect(url_for('coordinator.task_detail', task_id=task_id))

@coordinator_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
@coordinator_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    Assignment.query.filter_by(task_id=task_id).delete()
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'info')
    return redirect(url_for('coordinator.tasks'))

@coordinator_bp.route('/volunteers')
@login_required
@coordinator_required
def volunteers():
    all_volunteers = User.query.filter_by(role='volunteer').order_by(User.created_at.desc()).all()
    return render_template('coordinator/volunteers.html', volunteers=all_volunteers)

@coordinator_bp.route('/impact')
@login_required
@coordinator_required
def impact():
    total_volunteers  = User.query.filter_by(role='volunteer').count()
    total_tasks       = Task.query.count()
    completed_tasks   = Task.query.filter_by(status='completed').count()
    total_assignments = Assignment.query.count()
    completed_assignments = Assignment.query.filter_by(status='completed').count()
    accepted_assignments  = Assignment.query.filter_by(status='accepted').count()
    declined_assignments  = Assignment.query.filter_by(status='declined').count()
    impact_hours      = completed_assignments * 3

    # Skills frequency across all volunteers
    all_volunteers = User.query.filter_by(role='volunteer').all()
    skill_count = {}
    for v in all_volunteers:
        for s in v.get_skills():
            skill_count[s] = skill_count.get(s, 0) + 1
    top_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:8]

    # Task status breakdown for chart
    open_tasks       = Task.query.filter_by(status='open').count()
    inprogress_tasks = Task.query.filter_by(status='in-progress').count()

    return render_template('coordinator/impact.html',
        total_volunteers=total_volunteers,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        total_assignments=total_assignments,
        completed_assignments=completed_assignments,
        accepted_assignments=accepted_assignments,
        declined_assignments=declined_assignments,
        impact_hours=impact_hours,
        top_skills=top_skills,
        open_tasks=open_tasks,
        inprogress_tasks=inprogress_tasks,
    )

@coordinator_bp.route('/assign/<int:user_id>/<int:task_id>', methods=['POST'])
@login_required
@coordinator_required
def assign(user_id, task_id):
    existing = Assignment.query.filter_by(user_id=user_id, task_id=task_id).first()
    if existing:
        flash('This volunteer is already assigned to this task.', 'warning')
        return redirect(url_for('coordinator.task_detail', task_id=task_id))

    score = request.form.get('match_score', 0)
    assignment = Assignment(user_id=user_id, task_id=task_id, match_score=float(score))
    db.session.add(assignment)

    task = Task.query.get(task_id)
    if task and task.status == 'open':
        task.status = 'in-progress'

    db.session.commit()
    user = User.query.get(user_id)
    flash(f'{user.name} has been assigned to this task.', 'success')
    return redirect(url_for('coordinator.task_detail', task_id=task_id))

@coordinator_bp.route('/assignment/<int:assignment_id>/complete', methods=['POST'])
@login_required
@coordinator_required
def complete_assignment(assignment_id):
    a = Assignment.query.get_or_404(assignment_id)
    a.status = 'completed'
    db.session.commit()
    flash('Assignment marked as completed.', 'success')
    return redirect(url_for('coordinator.task_detail', task_id=a.task_id))
