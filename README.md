# Placement Management System (Flask + SQL edition)

A college placement portal converted from FastAPI to **Flask**, using **SQLAlchemy** (SQLite locally / PostgreSQL on Render) and server-rendered **Jinja2** templates.

## What's new vs. the original project

- **Framework**: rewritten on Flask (blueprints for `auth`, `admin`, `student`) instead of FastAPI routers.
- **Hashed passwords**: passwords are now stored with `werkzeug.security` hashes instead of plain text.
- **Resume file upload**: students can upload a PDF/DOC/DOCX (max 5 MB) in addition to, or instead of, a resume link. Files are served from `/static/uploads/`.
- **Search & filters**: search jobs (student + admin views), search/filter applications by student name/email/branch, search/filter the student directory by name/email/branch.
- **CSV export**: admins can export the current filtered list of applications as a CSV file.
- **In-app notifications**: students get a notification (with unread badge in the navbar) whenever the admin marks their application Selected/Rejected. If `SMTP_HOST` and related env vars are set, the same message is also emailed; otherwise it stays in-app only.
- **Admin analytics dashboard**: Chart.js charts for applications by status, top jobs by application volume, and student distribution by branch.
- **Admin students directory**: a searchable table of all registered students with resume links.

## Project layout

```
app.py                 # Flask app factory, blueprint registration, admin auto-seed
config.py              # Env-driven configuration (DB URL, upload limits, optional SMTP)
extensions.py          # Flask-SQLAlchemy instance
models.py              # User, Job, Application, Notification
auth.py                # Session-based login/role decorators
utils.py                # CGPA/eligibility helpers, job status, uploads, notifications/email
blueprints/
  auth_bp.py            # /, /login, /register, /logout
  admin_bp.py            # /admin/* (dashboard, jobs, applications, students, analytics, CSV export)
  student_bp.py          # /student/* (dashboard, profile, jobs, apply, notifications)
templates/              # Jinja2 templates (shared base.html with sidebar + flash messages)
static/style.css        # Styling (unchanged look, small additions for charts/badges)
static/uploads/         # Uploaded resume files land here
seed_admin.py           # Optional one-off script to (re)create the admin account
render.yaml             # Render.com deploy config (gunicorn + Postgres)
```

## Running locally

```bash
pip install -r requirements.txt
python app.py            # http://localhost:5000, SQLite file placement.db is created automatically
```

The admin account `admin@college.com` / `admin123` is seeded automatically on first run (or via `python seed_admin.py`).

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing key | dev key (change in production) |
| `DATABASE_URL` | SQLAlchemy DB URL (Postgres on Render, SQLite locally) | `sqlite:///placement.db` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` | Optional — enables emailing notifications in addition to in-app notifications | unset (email disabled) |

## Deploying to Render

`render.yaml` provisions a free Postgres database and a web service that runs
`gunicorn app:app`. Push this project to a Git repo and connect it on Render,
or use `render deploy` if you have the Render CLI configured.
