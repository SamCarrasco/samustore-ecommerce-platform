from flask import Flask, url_for, render_template, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config, ProdConfig
from flask_migrate import Migrate
import unicodedata
import re


db = SQLAlchemy()
migrate = Migrate(compare_type=True)
login_manager = LoginManager()

def slugify(value: str) -> str:
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^a-zA-Z0-9\s-]', '', value).strip().lower()
    value = re.sub(r'[\s_-]+', '-', value)
    return value

def create_app(config_object = Config):
    app = Flask(__name__, static_folder='static', static_url_path='/')
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @app.route("/")
    def landing():
        return render_template("landing.html", current_app = current_app)

    # Exponer slugify a Jinja:
    @app.context_processor
    def inject_helpers():
        return dict(slugify=slugify)

    # Registrar Blueprints
    from app.routes import auth, dashboard, public
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(public.bp)

    # user loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    def image_url(rel_path):
        # Si ya es una URL externa, la devolvemos tal cual
        if rel_path.startswith("http://") or rel_path.startswith("https://"):
            return rel_path
        return url_for('static', filename=rel_path)

    @app.context_processor
    def inject_helpers():
        return dict(slugify=slugify, image_url=image_url)

    def digits_filter(s):
        return re.sub(r'\D+', '', s or '')

    @app.template_filter('digits')
    def _digits_filter(s):
        return digits_filter(s)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html', error=e), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html', error=e), 500

    return app