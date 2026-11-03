from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from auth import student_required
from extensions import db
from models import Application, Job, Notification
from utils import (
    is_valid_cgpa,
    job_is_open,
    job_status_info,
    meets_cgpa_requirement,
    profile_complete,
    save_resume_file,
)

bp = Blueprint("student", __name__, url_prefix="/student")


def _closed_job_message(job):
    info = job_status_info(job)
    return info["reason"] or "This job is no longer accepting applications."


@bp.route("/dashboard")
@student_required
def dashboard():
    user = g.user
    jobs_applied = Application.query.filter_by(student_id=user.id).count()
    selected_count = Application.query.filter_by(student_id=user.id, status="Selected").count()
    pending_count = Application.query.filter_by(student_id=user.id, status="Pending").count()
    open_jobs = [job for job in Job.query.order_by(Job.posted_on.desc()).all() if job_is_open(job)]

    recent_applications = (
        Application.query.filter_by(student_id=user.id)
        .order_by(Application.applied_on.desc())
        .limit(3)
        .all()
    )
    unread_notifications = Notification.query.filter_by(user_id=user.id, is_read=False).count()

    return render_template(
        "student_dashboard.html",
        jobs_applied=jobs_applied,
        selected_count=selected_count,
        pending_count=pending_count,
        open_jobs_count=len(open_jobs),
        profile_complete=profile_complete(user),
        recent_applications=recent_applications,
        unread_notifications=unread_notifications,
    )


@bp.route("/profile", methods=["GET"])
@student_required
def profile_page():
    return render_template("student_profile.html")


@bp.route("/profile", methods=["POST"])
@student_required
def update_profile():
    user = g.user
    cgpa = request.form.get("cgpa", "").strip()
    branch = request.form.get("branch", "").strip()
    phone = request.form.get("phone", "").strip()
    resume_link = request.form.get("resume_link", "").strip()
    resume_file = request.files.get("resume_file")

    if not is_valid_cgpa(cgpa):
        flash("Enter a valid CGPA between 0 and 10.", "error")
        return render_template("student_profile.html")

    if not branch or not phone:
        flash("All profile fields are required.", "error")
        return render_template("student_profile.html")

    if not resume_link and not resume_file and not user.resume_filename:
        flash("Provide a resume link or upload a resume file.", "error")
        return render_template("student_profile.html")

    saved_filename = save_resume_file(resume_file, user.id)
    if resume_file and resume_file.filename and not saved_filename:
        flash("Resume must be a PDF, DOC, or DOCX file (max 5 MB).", "error")
        return render_template("student_profile.html")

    user.cgpa = cgpa
    user.branch = branch
    user.phone = phone
    user.resume_link = resume_link or user.resume_link
    if saved_filename:
        user.resume_filename = saved_filename
    db.session.commit()
    flash("Profile saved. You can now apply to open jobs.", "success")
    return redirect(url_for("student.profile_page"))


@bp.route("/jobs")
@student_required
def jobs():
    search = request.args.get("q", "").strip()
    query = Job.query
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(Job.title.ilike(like), Job.company.ilike(like)))

    all_jobs = [job for job in query.order_by(Job.posted_on.desc()).all() if job_is_open(job)]
    applied_job_ids = [
        app.job_id for app in Application.query.filter_by(student_id=g.user.id).all()
    ]

    return render_template(
        "job_list.html",
        jobs=all_jobs,
        applied_job_ids=applied_job_ids,
        profile_complete=profile_complete(g.user),
        meets_cgpa_requirement=meets_cgpa_requirement,
        search=search,
    )


@bp.route("/apply/<int:job_id>", methods=["GET"])
@student_required
def apply_form(job_id):
    user = g.user
    job = Job.query.get(job_id)
    if job is None:
        flash("Job not found.", "error")
        return redirect(url_for("student.jobs"))

    if not job_is_open(job):
        flash(_closed_job_message(job), "error")
        return redirect(url_for("student.jobs"))

    if not profile_complete(user):
        flash("Complete your profile before applying.", "error")
        return redirect(url_for("student.profile_page"))

    already_applied = Application.query.filter_by(student_id=user.id, job_id=job_id).first()
    if already_applied:
        flash("You have already applied to this job.", "info")
        return redirect(url_for("student.my_applications"))

    eligible = meets_cgpa_requirement(user.cgpa, job.min_cgpa)
    return render_template("apply_job.html", job=job, eligible=eligible)


@bp.route("/apply/<int:job_id>", methods=["POST"])
@student_required
def apply(job_id):
    user = g.user
    cover_letter = request.form.get("cover_letter", "").strip()

    job = Job.query.get(job_id)
    if job is None:
        flash("Job not found.", "error")
        return redirect(url_for("student.jobs"))

    if not job_is_open(job):
        flash(_closed_job_message(job), "error")
        return redirect(url_for("student.jobs"))

    if not profile_complete(user):
        flash("Complete your profile before applying.", "error")
        return redirect(url_for("student.profile_page"))

    if not meets_cgpa_requirement(user.cgpa, job.min_cgpa):
        flash("You do not meet the minimum CGPA for this job.", "error")
        return redirect(url_for("student.jobs"))

    if not cover_letter:
        flash("Cover letter cannot be empty.", "error")
        return redirect(url_for("student.apply_form", job_id=job_id))

    already_applied = Application.query.filter_by(student_id=user.id, job_id=job_id).first()
    if already_applied:
        flash("You have already applied to this job.", "info")
        return redirect(url_for("student.my_applications"))

    application = Application(
        student_id=user.id,
        job_id=job_id,
        status="Pending",
        cgpa=user.cgpa,
        branch=user.branch,
        phone=user.phone,
        resume_link=user.resume_link,
        resume_filename=user.resume_filename,
        cover_letter=cover_letter,
    )
    db.session.add(application)
    db.session.commit()
    flash(f"Application submitted for {job.title} at {job.company}", "success")
    return redirect(url_for("student.my_applications"))


@bp.route("/my-applications")
@student_required
def my_applications():
    applications = (
        Application.query.filter_by(student_id=g.user.id)
        .order_by(Application.applied_on.desc())
        .all()
    )
    return render_template(
        "my_applications.html", applications=applications, job_status_info=job_status_info
    )


@bp.route("/notifications")
@student_required
def notifications():
    all_notifications = (
        Notification.query.filter_by(user_id=g.user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    Notification.query.filter_by(user_id=g.user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return render_template("notifications.html", notifications=all_notifications)
