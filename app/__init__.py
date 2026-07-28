import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()

def create_app(test_config=None):
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    CORS(app)

    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    default_db_path = os.path.join(base_dir, "hr_payroll.db")

    database_url = os.environ.get("DATABASE_URL", f"sqlite:///{default_db_path}")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from app.routes.employees import employees_bp
    from app.routes.leave import leave_bp
    from app.routes.payroll import payroll_bp

    app.register_blueprint(employees_bp, url_prefix="/api/employees")
    app.register_blueprint(leave_bp, url_prefix="/api/leave")
    app.register_blueprint(payroll_bp, url_prefix="/api/payroll")

    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    return app