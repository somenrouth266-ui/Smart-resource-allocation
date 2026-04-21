import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
from datetime import datetime

# load_dotenv() is used for local development. 
# On Railway, it will safely skip if no .env file is found.
load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # --- CONFIGURATION ---
    # Secret key for session management
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')

    # Database configuration (SQLAlchemy 3.0+ compatibility for Postgres)
    database_url = os.getenv('DATABASE_URL', 'sqlite:///volunteer.db')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # AI API Keys - Pulling directly from Railway Environment Variables
    app.config['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY', '')
    app.config['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')

    # --- INITIALIZATION ---
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    with app.app_context():
        # Import models to ensure they are registered with SQLAlchemy
        from models import User, Task, Assignment

        # Import and register Blueprints
        from routes.auth import auth_bp
        from routes.coordinator import coordinator_bp
        from routes.volunteer import volunteer_bp
        from routes.main import main_bp
        from routes.ai_suggest import ai_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp,         url_prefix='/auth')
        app.register_blueprint(coordinator_bp,  url_prefix='/coordinator')
        app.register_blueprint(volunteer_bp,    url_prefix='/volunteer')
        app.register_blueprint(ai_bp,           url_prefix='/ai')

        # --- ERROR HANDLERS ---
        @app.errorhandler(404)
        def not_found(e):
            return render_template('errors/404.html'), 404

        @app.errorhandler(500)
        def server_error(e):
            return render_template('errors/500.html'), 500

        # --- CONTEXT PROCESSORS ---
        @app.context_processor
        def inject_globals():
            return {
                'now_hour': datetime.now().hour,
                'current_year': datetime.now().year,
            }

        # Create database tables if they don't exist
        db.create_all()

    return app
