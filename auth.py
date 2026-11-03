from functools import wraps

from flask import g, redirect, session, url_for, abort

from models import User


def load_current_user():
    """Called before each request to populate flask.g.user from the session."""
    user_id = session.get("user_id")
    g.user = User.query.get(user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)

    return wrapped


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login_page"))
        if g.user.role != "student":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login_page"))
        if g.user.role != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped
