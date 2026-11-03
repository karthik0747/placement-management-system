"""Run once to create the admin account: python seed_admin.py"""

from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import User

app = create_app()

with app.app_context():
    existing = User.query.filter_by(email="admin@college.com").first()
    if existing:
        print("Admin already exists.")
    else:
        admin = User(
            name="Admin",
            email="admin@college.com",
            password_hash=generate_password_hash("admin123"),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin created! Login with admin@college.com / admin123")
