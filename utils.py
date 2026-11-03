import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from flask import current_app
from werkzeug.utils import secure_filename

from extensions import db
from models import Notification


# ---------- CGPA / eligibility helpers ----------

def parse_cgpa(value):
    if value is None or value == "":
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def is_valid_cgpa(value) -> bool:
    cgpa = parse_cgpa(value)
    return cgpa is not None and 0 <= cgpa <= 10


def profile_complete(user) -> bool:
    return bool(
        user.cgpa
        and user.branch
        and user.phone
        and (user.resume_link or user.resume_filename)
        and is_valid_cgpa(user.cgpa)
    )


def meets_cgpa_requirement(user_cgpa, min_cgpa) -> bool:
    if min_cgpa is None or min_cgpa == "":
        return True
    student_cgpa = parse_cgpa(user_cgpa)
    min_value = parse_cgpa(min_cgpa)
    if student_cgpa is None or min_value is None:
        return False
    return student_cgpa >= min_value


# ---------- Job status helpers ----------

def job_status_info(job) -> dict:
    if getattr(job, "status", None) == "closed":
        return {"open": False, "label": "Closed", "reason": "Closed by placement cell"}
    if job.deadline and datetime.utcnow() > job.deadline:
        return {"open": False, "label": "Closed", "reason": "Application deadline passed"}
    return {"open": True, "label": "Open", "reason": None}


def job_is_open(job) -> bool:
    return job_status_info(job)["open"]


# ---------- File uploads ----------

def allowed_resume_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_RESUME_EXTENSIONS"]


def save_resume_file(file_storage, user_id: int):
    """Save an uploaded resume file, return the stored filename or None."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_resume_file(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = secure_filename(f"resume_user{user_id}_{int(datetime.utcnow().timestamp())}.{ext}")
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return filename


# ---------- Notifications (in-app + optional email) ----------

def notify_user(user, message: str, link: str = None):
    """Create an in-app notification and, if SMTP is configured, email it too."""
    note = Notification(user_id=user.id, message=message, link=link)
    db.session.add(note)
    db.session.commit()
    _send_email_if_configured(user, message)


def _send_email_if_configured(user, message: str):
    host = current_app.config.get("SMTP_HOST")
    if not host or not user.email:
        return  # Email not configured — in-app notification is enough.
    try:
        msg = MIMEText(message)
        msg["Subject"] = "PlacementMS Notification"
        msg["From"] = current_app.config["MAIL_FROM"]
        msg["To"] = user.email
        with smtplib.SMTP(host, current_app.config["SMTP_PORT"], timeout=5) as server:
            server.starttls()
            user_name = current_app.config.get("SMTP_USER")
            password = current_app.config.get("SMTP_PASSWORD")
            if user_name and password:
                server.login(user_name, password)
            server.sendmail(msg["From"], [user.email], msg.as_string())
    except Exception:
        # Never let email failures break the request; notification is still saved in-app.
        current_app.logger.warning("Email notification failed to send.", exc_info=True)
