import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "placement_secret_key_dev_only")

    _raw_url = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'placement.db')}")
    if _raw_url.startswith("postgres://"):
        _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_RESUME_EXTENSIONS = {"pdf", "doc", "docx"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload

    # Optional outbound email (only used if SMTP_HOST is set; otherwise
    # notifications are stored in-app only and email sending is skipped).
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM", "placements@college.edu")
