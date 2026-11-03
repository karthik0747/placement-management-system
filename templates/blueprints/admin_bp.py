import csv
import io
from datetime import datetime

from flask import Blueprint, Response, flash, g, redirect, render_template, request, url_for

from auth import admin_required
from extensions import db
from models import Application, Job, User
from utils import job_is_open, job_status_info, notify_user

bp = Blueprint("admin", __name__, url_prefix="/admin")

VALID_APPLICATION_STATUSES = {"Pending", "Selected", "Rejected"}


@bp.route("/dashboard")
@admin_required
def dashboard():
    total_students = User.query.filter_by(role="student").count()
    total_jobs = Job.query.count()
    total_applications = Application.query.count()
    pending_reviews = Application.query.filter_by(status="Pending").count()
    open_jobs = sum(1 for job in Job.query.all() if job_is_open(job))

    recent_applications = (
        Application.query.order_by(Application.applied_on.desc()).limit(5).all()
    )

    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_jobs=total_jobs,
        total_applications=total_applications,
        pending_reviews=pending_reviews,
        open_jobs=open_jobs,
        recent_applications=recent_applications,
    )


@bp.route("/post-job", methods=["GET"])
@admin_required
def post_job_page():
    return render_template("post_job.html", today=datetime.utcnow().strftime("%Y-%m-%d"))


@bp.route("/post-job", methods=["POST"])
@admin_required
def post_job():
    title = request.form.get("title", "").strip()
    company = request.form.get("company", "").strip()
    description = request.form.get("description", "").strip()
    package = request.form.get("package", "").strip()
    eligibility = request.form.get("eligibility", "").strip()
    min_cgpa = request.form.get("min_cgpa", "").strip()
    deadline = request.form.get("deadline", "").strip()
    company_portal_url = request.form.get("company_portal_url", "").strip()

    deadline_dt = None
    if deadline:
        deadline_dt = datetime.strptime(deadline, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
        if deadline_dt < datetime.utcnow():
            flash("Deadline cannot be in the past.", "error")
            return render_template("post_job.html", today=datetime.utcnow().strftime("%Y-%m-%d"))

    job = Job(
        title=title,
        company=company,
        description=description,
        package=package,
        eligibility=eligibility,
        min_cgpa=min_cgpa or None,
        deadline=deadline_dt,
        company_portal_url=company_portal_url or None,
        status="open",
    )
    db.session.add(job)
    db.session.commit()
    flash(f"Job posted: {title} at {company}", "success")
    return redirect(url_for("admin.jobs"))


@bp.route("/jobs")
@admin_required
def jobs():
    search = request.args.get("q", "").strip()
    query = Job.query
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Job.title.ilike(like), Job.company.ilike(like)))
    all_jobs = query.order_by(Job.posted_on.desc()).all()

    job_stats = {job.id: Application.query.filter_by(job_id=job.id).count() for job in all_jobs}

    return render_template(
        "job_list_admin.html",
        jobs=all_jobs,
        job_stats=job_stats,
        job_is_open=job_is_open,
        job_status_info=job_status_info,
        search=search,
    )


@bp.route("/jobs/<int:job_id>/close", methods=["POST"])
@admin_required
def close_job(job_id):
    job = Job.query.get(job_id)
    if job is None:
        flash("Job not found.", "error")
        return redirect(url_for("admin.jobs"))
    job.status = "closed"
    db.session.commit()
    flash(f"Closed {job.title} at {job.company}. No new applications accepted.", "success")
    return redirect(url_for("admin.jobs"))


@bp.route("/jobs/<int:job_id>/reopen", methods=["POST"])
@admin_required
def reopen_job(job_id):
    job = Job.query.get(job_id)
    if job is None:
        flash("Job not found.", "error")
        return redirect(url_for("admin.jobs"))
    job.status = "open"
    db.session.commit()

    info = job_status_info(job)
    if info["open"]:
        flash(f"Reopened {job.title} at {job.company}. Students can apply again.", "success")
    else:
        flash(
            f"Reopened {job.title}, but deadline has passed — post a new drive so students can apply.",
            "warning",
        )
    return redirect(url_for("admin.jobs"))


@bp.route("/applications")
@admin_required
def applications():
    status = request.args.get("status", "all")
    job_id = request.args.get("job_id", "")
    search = request.args.get("q", "").strip()

    query = Application.query
    if status != "all":
        query = query.filter(Application.status == status)
    if job_id:
        query = query.filter(Application.job_id == int(job_id))
    if search:
        like = f"%{search}%"
        query = query.join(User, Application.student_id == User.id).filter(
            db.or_(User.name.ilike(like), User.email.ilike(like), Application.branch.ilike(like))
        )

    all_applications = query.order_by(Application.applied_on.desc()).all()
    all_jobs = Job.query.order_by(Job.company).all()
    selected_job_id = int(job_id) if job_id.isdigit() else None

    return render_template(
        "applications.html",
        applications=all_applications,
        all_jobs=all_jobs,
        selected_status=status,
        selected_job_id=selected_job_id,
        search=search,
    )


@bp.route("/applications/export.csv")
@admin_required
def export_applications_csv():
    status = request.args.get("status", "all")
    job_id = request.args.get("job_id", "")

    query = Application.query
    if status != "all":
        query = query.filter(Application.status == status)
    if job_id:
        query = query.filter(Application.job_id == int(job_id))
    rows = query.order_by(Application.applied_on.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Student", "Email", "Job", "Company", "CGPA", "Branch", "Phone", "Status", "Applied On"]
    )
    for app in rows:
        writer.writerow(
            [
                app.student.name,
                app.student.email,
                app.job.title,
                app.job.company,
                app.cgpa or "",
                app.branch or "",
                app.phone or "",
                app.status,
                app.applied_on.strftime("%Y-%m-%d %H:%M") if app.applied_on else "",
            ]
        )

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )


@bp.route("/applications/<int:application_id>")
@admin_required
def application_detail(application_id):
    application = Application.query.get(application_id)
    if application is None:
        flash("Application not found.", "error")
        return redirect(url_for("admin.applications"))

    return render_template(
        "application_detail.html", app=application, job_status_info=job_status_info
    )


@bp.route("/applications/<int:application_id>/update", methods=["POST"])
@admin_required
def update_application(application_id):
    status = request.form.get("status", "")
    if status not in VALID_APPLICATION_STATUSES:
        flash("Invalid status value.", "error")
        return redirect(url_for("admin.applications"))

    application = Application.query.get(application_id)
    if application is None:
        flash("Application not found.", "error")
        return redirect(url_for("admin.applications"))

    application.status = status
    db.session.commit()

    if status in ("Selected", "Rejected"):
        notify_user(
            application.student,
            f"Your application for {application.job.title} at {application.job.company} was marked {status}.",
            link=url_for("student.my_applications"),
        )

    flash(f"Status updated to {status}", "success")
    return redirect(url_for("admin.application_detail", application_id=application_id))


@bp.route("/students")
@admin_required
def students():
    search = request.args.get("q", "").strip()
    branch = request.args.get("branch", "").strip()

    query = User.query.filter_by(role="student")
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))
    if branch:
        query = query.filter(User.branch == branch)

    all_students = query.order_by(User.name).all()
    branches = sorted(
        {u.branch for u in User.query.filter_by(role="student").all() if u.branch}
    )

    return render_template(
        "students_admin.html",
        students=all_students,
        branches=branches,
        search=search,
        selected_branch=branch,
    )


@bp.route("/analytics")
@admin_required
def analytics():
    status_counts = {
        status: Application.query.filter_by(status=status).count()
        for status in ("Pending", "Selected", "Rejected")
    }

    jobs_with_counts = (
        db.session.query(Job.title, Job.company, db.func.count(Application.id))
        .outerjoin(Application, Application.job_id == Job.id)
        .group_by(Job.id)
        .order_by(db.func.count(Application.id).desc())
        .limit(8)
        .all()
    )
    job_labels = [f"{title} ({company})" for title, company, _ in jobs_with_counts]
    job_counts = [count for _, _, count in jobs_with_counts]

    branch_counts_raw = (
        db.session.query(User.branch, db.func.count(User.id))
        .filter(User.role == "student", User.branch.isnot(None))
        .group_by(User.branch)
        .all()
    )
    branch_labels = [b for b, _ in branch_counts_raw]
    branch_counts = [c for _, c in branch_counts_raw]

    return render_template(
        "analytics.html",
        status_counts=status_counts,
        job_labels=job_labels,
        job_counts=job_counts,
        branch_labels=branch_labels,
        branch_counts=branch_counts,
    )
