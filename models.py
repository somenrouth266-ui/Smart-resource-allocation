from flask_login import UserMixin
from datetime import datetime
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    role         = db.Column(db.String(20), nullable=False, default='volunteer')
    skills       = db.Column(db.String(300), nullable=True)
    availability = db.Column(db.String(300), nullable=True)
    bio          = db.Column(db.String(500), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    assignments  = db.relationship('Assignment', backref='user', lazy=True)

    def get_skills(self):
        if self.skills:
            return [s.strip().lower() for s in self.skills.split(',') if s.strip()]
        return []

    def get_availability(self):
        if self.availability:
            return [a.strip() for a in self.availability.split(',') if a.strip()]
        return []

    def completed_tasks_count(self):
        return Assignment.query.filter_by(user_id=self.id, status='completed').count()

    def active_tasks_count(self):
        return Assignment.query.filter_by(user_id=self.id, status='accepted').count()

    def impact_hours(self):
        # Each completed task = 3 hours (simple estimate)
        return self.completed_tasks_count() * 3

    def __repr__(self):
        return f'<User {self.name} | {self.role}>'


class Task(db.Model):
    __tablename__ = 'tasks'

    id              = db.Column(db.Integer, primary_key=True)
    title           = db.Column(db.String(150), nullable=False)
    description     = db.Column(db.Text, nullable=True)
    required_skills = db.Column(db.String(300), nullable=True)
    time_slot       = db.Column(db.String(100), nullable=True)
    location        = db.Column(db.String(200), nullable=True)
    volunteers_needed = db.Column(db.Integer, default=1)
    priority        = db.Column(db.String(20), nullable=False, default='medium')  # low / medium / high
    status          = db.Column(db.String(30), nullable=False, default='open')    # open / in-progress / completed
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    assignments     = db.relationship('Assignment', backref='task', lazy=True)

    def get_required_skills(self):
        if self.required_skills:
            return [s.strip().lower() for s in self.required_skills.split(',') if s.strip()]
        return []

    def accepted_volunteers_count(self):
        return Assignment.query.filter_by(task_id=self.id, status='accepted').count()

    def is_full(self):
        return self.accepted_volunteers_count() >= self.volunteers_needed

    def __repr__(self):
        return f'<Task {self.title} | {self.status}>'


class Assignment(db.Model):
    __tablename__ = 'assignments'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id     = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    status      = db.Column(db.String(30), nullable=False, default='pending')  # pending / accepted / declined / completed
    match_score = db.Column(db.Float, default=0.0)   # skill match score 0-100
    ai_reason   = db.Column(db.Text, nullable=True)  # AI suggestion reason
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Assignment User:{self.user_id} Task:{self.task_id} | {self.status}>'
