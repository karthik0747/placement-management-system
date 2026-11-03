from flask import Flask, g, get_flashed_messages, render_template, request
from werkzeug.security import generate_password_hash

from auth import load_current_user
from config import Config
from extensions import db
from models import Notification, User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from blueprints.auth_bp import bp as auth_bp
    from blueprints.admin_bp import bp as admin_bp
    from blueprints.student_bp import bp as student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)

    @app.before_request
    def _load_user():
        load_current_user()

    @app.context_processor
    def inject_globals():
        unread = 0
        if g.get("user") and g.user.role == "student":
            unread = Notification.query.filter_by(user_id=g.user.id, is_read=False).count()
        return {
            "current_user": g.get("user"),
            "request": request,
            "unread_notifications": unread,
        }

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("login.html", error="You don't have access to that page."), 403

    with app.app_context():
        db.create_all()
        _seed_admin_if_missing()

    return app


def _seed_admin_if_missing():
    existing = User.query.filter_by(email="admin@college.com").first()
    if not existing:
        db.session.add(
            User(
                name="Admin",
                email="admin@college.com",
                password_hash=generate_password_hash("admin123"),
                role="admin",
            )
        )
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    import os

    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
