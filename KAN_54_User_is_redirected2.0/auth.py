
#Importing core Flask utilities for routing, rendering templates, handling form data, flashinf messages and redirects
from flask import Blueprint, render_template, request, flash, redirect, url_for


#Importing for secure password hashing and verification
from werkzeug.security import generate_password_hash, check_password_hash

#Import flask-login utilities for session management
from flask_login import UserMixin, login_user, login_required, logout_user

#PostgreSQL driver and error handling
import psycopg
from psycopg import errors

#import database connection helper
from .db import get_db

#Creating authentication blueprint with URL prefix "/auth"
##!!all routes in this file should be under /auth/* !!
bp = Blueprint("auth", __name__, url_prefix="/auth")


#Creating the user class needed to login

#Flask-login needs a user object with 'id' attribute
#UserMixin will provide the required authentication properties --> if a user has logged in, if the account is 
#active, if the account is not authenticated yet (anonymous)
class User(UserMixin):
    def __init__(self, id, email):
        self.id=id #unique user id
        self.email=email #stored for convenience



#Registering the user route
@bp.route("/register",methods=("GET","POST"))
def register():
    #if the user submits the registration form
    if request.method == "POST":
        
        #retrieve and clean form inputs
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        error = None

        #basic input validation
        if not email:
            error = "Email required"
        elif not password:
            error = "Password required"

        #if no validation errors, attempt to insert into database
        if error is None:
            db = get_db()
            try:
                with db.cursor() as cur:
                    #inserting new user with securely hashed password
                    cur.execute(
                        "INSERT INTO users (email,password_hash) VALUES (%s, %s)",
                        (email, generate_password_hash(password)),
                    )
                    db.commit()
                    #after successful registration, redirect to login page
                    return redirect(url_for("auth.login"))

            #handle duplicate emails (UniqueViolation) 
            except errors.UniqueViolation:
                db.rollback()
                error = "Email already registered."

            #Catch any other database-related errors
            except psycopg.Error:
                db.rollback()
                error = "Database error. Please try again."
        
        #Display error message to user
        flash(error)
    
    #Render registration template if GET request    
    return render_template("auth/register.html")

#Logging in -- should handle login form display and authentication verification
@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        
        #Retrieve and clean submitted credentials
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        #Query database for matching email
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash FROM users WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()

        error = None

        #Validate credentials
        if user is None:
            error = "Incorrect email."
        elif not check_password_hash(user["password_hash"], password):
            
            #Securely compare submitted password with stored hash
            error = "Incorrect password."

        # If credentials are correct   
        if error is None:

            #Create user session (Stores user ID in session cookie)
            login_user(User(user["id"], user["email"]))
            return redirect(url_for("home.index"))
        
        #If login fails, display error
        flash(error)

    #Render login page on GET request    
    return render_template("auth/login.html")


#logging out
#should end the user session securely
@bp.route("/logout")

#Only authenticated users can access the logout
@login_required
def logout():

    #Clears session data and removes user authentication
    logout_user()

    #Redirects users to login page after logging out
    return redirect(url_for("auth.login"))



#What this code does
# Passwords are hashed securely before storage
# Passwords are verified securely using hash comparison
# Duplicate email registration is handled safely
# Login sessions are created using Flask-login
# Routes can be protected using @login_required
# Logout properly terminates the session
