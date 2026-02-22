### REGISTRATION + LOGIN FOR USERS ####


from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg
from psycopg import errors
from flask_login import UserMixin, login_user, login_required, logout_user
from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")

### Setting up User Class ###

class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email


### REGISTRATION FOR NEW USERS ROUTE ###

@bp.route("/register", methods  = ("GET", "POST"))
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        error = None
        if not email:
            error = "Email Required"
        elif not password:
            error = "Password Required"
        
        if error is None:
            db = get_db()
            try:    
                with db.cursor() as cur:
                    cur.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (email, generate_password_hash(password)), )
                db.commit()
                return redirect(url_for("auth.login"))
            
            except errors.UniqueViolation:
                db.rollback()
                error = "Email you have entered is already in use. Try logging in instead."

            except psycopg.Error:
                db.rollback()
                error = "Error. Please try again."
        
        flash(error)
    
    return render_template("auth/register.html")

### LOGIN FOR EXISTING USERS ROUTE ###

@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or "" 

        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash FROM users WHERE email = %s", (email,),)
            user = cur.fetchone()
        error = None

        if user is None:
            error = "Incorrect email or password. Please try again."
        elif not check_password_hash(user["password_hash"], password):
            error = "Incorrect email or password. Please try again."

        if error is None:
            login_user(User(user["id"], user["email"]))
            return redirect(url_for("home.dashboard"))
    
        flash(error)
    
    return render_template("auth/login.html")

### LOG OUT ROUTE ###

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home.index"))
