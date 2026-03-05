from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg
from psycopg import errors as pg_errors
from flask_login import UserMixin, login_user, login_required, logout_user
from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")


class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        error = None
        if not email:
            error = "Email is required."
        elif not password:
            error = "Password is required."

        if error is None:
            db = get_db()
            try:
                with db.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
                        (email, generate_password_hash(password)),
                    )
                db.commit()
                return redirect(url_for("auth.login"))
            except pg_errors.UniqueViolation:
                db.rollback()
                error = "That email is already registered. Try logging in."
            except psycopg.Error:
                db.rollback()
                error = "A database error occurred. Please try again."

        flash(error)

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash FROM users WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()

        error = None
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Incorrect email or password."

        if error is None:
            login_user(User(user["id"], user["email"]))
            return redirect(url_for("home.dashboard"))

        flash(error)

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home.index"))
