from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User

bp = Blueprint("auth", __name__)


def _home_for(user):
    return url_for("admin.dashboard") if user.role == "admin" else url_for("student.dashboard")


@bp.route("/")
def root():
    if g.user:
        return redirect(_home_for(g.user))
    return redirect(url_for("auth.login_page"))


@bp.route("/login", methods=["GET"])
def login_page():
    if g.user:
        return redirect(_home_for(g.user))
    return render_template("login.html")


@bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = User.query.filter(db.func.lower(User.email) == email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return render_template("login.html", error="Invalid credentials")

    session["user_id"] = user.id

    if user.role == "admin":
        flash(f"Welcome back, {user.name}", "success")
        return redirect(url_for("admin.dashboard"))
    flash("Welcome! Complete your profile to start applying.", "success")
    return redirect(url_for("student.dashboard"))


@bp.route("/register", methods=["GET"])
def register_page():
    if g.user:
        return redirect(_home_for(g.user))
    return render_template("register.html")


@bp.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required")

    existing = User.query.filter(db.func.lower(User.email) == email).first()
    if existing:
        return render_template("register.html", error="Email already registered")

    new_user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role="student",
    )
    db.session.add(new_user)
    db.session.commit()
    flash("Account created. Please log in and complete your profile.", "success")
    return redirect(url_for("auth.login_page"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
