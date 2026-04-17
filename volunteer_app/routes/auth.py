from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        email        = request.form.get('email', '').strip().lower()
        password     = request.form.get('password', '')
        confirm      = request.form.get('confirm_password', '')
        role         = request.form.get('role', 'volunteer')
        skills       = request.form.get('skills', '').strip()
        # availability comes from hidden input built by JS checkboxes
        availability = request.form.get('availability', '').strip()
        if not availability:
            # fallback: read checkbox values directly
            slots = request.form.getlist('avail_slots')
            availability = ','.join(slots)

        if not name or not email or not password:
            flash('Name, email and password are required.', 'error')
            return render_template('auth/register.html')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('auth/register.html')

        if role not in ('volunteer', 'coordinator'):
            role = 'volunteer'

        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return render_template('auth/register.html')

        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role,
            skills=skills,
            availability=availability
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f'Welcome, {user.name}! Your account has been created.', 'success')

        if user.role == 'coordinator':
            return redirect(url_for('coordinator.dashboard'))
        return redirect(url_for('volunteer.dashboard'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid email or password.', 'error')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)

        if user.role == 'coordinator':
            return redirect(url_for('coordinator.dashboard'))
        return redirect(url_for('volunteer.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))
