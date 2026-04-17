import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///volunteer.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    with app.app_context():
        from models import User, Task, Assignment

        # ── Blueprints ──
        from routes.auth import auth_bp
        from routes.coordinator import coordinator_bp
        from routes.volunteer import volunteer_bp
        from routes.main import main_bp
        from routes.ai_suggest import ai_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(coordinator_bp, url_prefix='/coordinator')
        app.register_blueprint(volunteer_bp, url_prefix='/volunteer')
        app.register_blueprint(ai_bp, url_prefix='/ai')

        # ── Error Handlers ──
        @app.errorhandler(404)
        def not_found(e):
            return "Page Not Found", 404

        @app.errorhandler(500)
        def server_error(e):
            return "Internal Server Error", 500

        # ── Context processor ──
        from datetime import datetime

        @app.context_processor
        def inject_globals():
            return {
                'now_hour': datetime.now().hour,
                'current_year': datetime.now().year,
            }

        db.create_all()

    return app
