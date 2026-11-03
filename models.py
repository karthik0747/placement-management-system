from datetime import datetime

from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)  # "student" or "admin"

    cgpa = db.Column(db.String)
    branch = db.Column(db.String)
    phone = db.Column(db.String)
    resume_link = db.Column(db.String)
    resume_filename = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship(
        "Application", back_populates="student", cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, nullable=False)
    company = db.Column(db.String, nullable=False)
    description = db.Column(db.String)
    package = db.Column(db.String)
    eligibility = db.Column(db.String)
    min_cgpa = db.Column(db.String)
    deadline = db.Column(db.DateTime)
    company_portal_url = db.Column(db.String)
    status = db.Column(db.String, default="open")  # "open" or "closed"
    posted_on = db.Column(db.DateTime, default=datetime.utcnow)

    applications = db.relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"))
    status = db.Column(db.String, default="Pending")  # Pending / Selected / Rejected
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)

    cgpa = db.Column(db.String)
    branch = db.Column(db.String)
    phone = db.Column(db.String)
    resume_link = db.Column(db.String)
    resume_filename = db.Column(db.String)
    cover_letter = db.Column(db.String)

    student = db.relationship("User", back_populates="applications")
    job = db.relationship("Job", back_populates="applications")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String, nullable=False)
    link = db.Column(db.String)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="notifications")
