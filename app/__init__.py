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

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{default_db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    return app