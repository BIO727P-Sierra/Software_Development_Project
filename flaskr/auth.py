from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash 
import psycopg
from psycopg import errors
from flask_login import UserMixin
from .db import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")

class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

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

@bp.route("/login", methods=("GET", "POST"))
def login():
    return render_template("auth/login.html")