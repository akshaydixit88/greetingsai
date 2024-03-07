import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from zxcvbn import zxcvbn
from helpers import apology, login_required, usd, is_strong_password, is_valid_email, generate_message, generate_image, generate_reset_token, save_image_from_url
import uuid
from emailhelper import send_reset_email

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///greetings.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    offset = int(request.args.get('offset', 0))
    user_messages = db.execute("SELECT * FROM user_message WHERE user_id = ? Order BY date_generated desc LIMIT 6 OFFSET ?", session["user_id"], offset*6)
    
    return render_template('index.html', user_messages = user_messages, offset=offset)



@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    existing_greetings_count = db.execute(
        "SELECT COUNT(*) as count FROM user_message WHERE user_id = ?",
        session["user_id"]
    )
    print(existing_greetings_count[0]['count'])

    if existing_greetings_count[0]['count'] >= 15:
        flash("You have already created the maximum number of greetings (15).")
        return redirect("/") 

    if request.method == "POST":
        name = request.form.get('name', 'Friend')
        occasion = request.form.get('occasion', 'occasion')
        message_type = request.form.get('message-type', 'message')
        relation = request.form.get('relation', 'friend')
        pictype = request.form.get('pic-type', 'animated')
        piccontext = request.form.get('pic-context', 'happy animals')

        # Generate greeting card content dynamically
        greeting_card_content = generate_message(name, occasion, message_type, relation)
        greeting_card_content = "<br>".join("<p>{}</p>".format(para) for para in greeting_card_content.split("\n\n"))

        # Use below proxy when Dall-E is not being called 
        # image_url = 'https://mastimorning.com/wp-content/uploads/2023/09/Happy-birthday-images-Photo-Download.jpg'

        # Generate greeting card image using Dall-E

        image_url = generate_image(occasion, pictype, piccontext) 

        new_url = save_image_from_url(image_url)

        # Use below proxy when directly accessing the link
        # new_url = image_url 
        
        unique_identifier = str(uuid.uuid4())


        # Save the message to the database using provided syntax
        db.execute(
            "INSERT INTO user_message (user_id, occasion, message_content, image_url, date_generated, unique_id) VALUES (?,?,?,?,?,?)",
            session["user_id"], occasion, greeting_card_content, new_url,datetime.utcnow(), unique_identifier
        )
        

        return render_template('create.html', greeting_card_content=greeting_card_content, image_url = new_url, id = unique_identifier)

    else:
        return render_template("create.html")


@app.route("/gallery")
@login_required
def inspire():
    general_messages = db.execute("SELECT * FROM user_message Order BY date_generated desc LIMIT 10")
    return render_template('gallery.html', general_messages = general_messages)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")




@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must create username", 400)

        # Ensure email was submitted and is valid
        email = request.form.get("email")
        if not email or not is_valid_email(email):
            return apology("must provide a valid email", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must create password", 400)

        # Ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords do not match", 400)
        

        # Check if the password is strong
        elif not is_strong_password(request.form.get("password")):
            return apology("Password is not strong enough", 400)
  

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        if len(rows) != 0:
            return apology("Username is already taken", 400)

        username = request.form.get("username")
        hash = generate_password_hash(request.form.get("password"), method='pbkdf2', salt_length=16)

        db.execute("INSERT INTO users (username, email, hash) VALUES (?,?,?)", username, email, hash)
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")



@app.route("/view_card/<unique_identifier>")
def view_card(unique_identifier):
    user_messages = db.execute("SELECT * FROM user_message WHERE unique_id = ?", unique_identifier)

    # Render the greeting card template
    return render_template("view_card.html", user_messages = user_messages)




@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username")

        # Check if username exists in your database
        user = db.execute("SELECT * FROM users WHERE username = ?", username)

        if user:
            # Generate a reset token and associate it with the user
            reset_token = generate_reset_token()
            # print(user[0]['id'])
            db.execute("UPDATE users SET reset_token = ? WHERE id = ?", reset_token, user[0]["id"])

            # Send the reset email (you need to implement this)
            # send_reset_email(user[0]["email"], reset_token)
            print("Email",user[0]["email"], "Token", reset_token)

            flash("Password reset email sent. Check your email for instructions.")
            return redirect(url_for("login"))
        else:
            flash("Username not found.")
            return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")




@app.route("/reset_password/<reset_token>", methods=["GET", "POST"])
def reset_password(reset_token):
    if request.method == "POST":
        new_password = request.form.get("new_password")

        # Validate the reset token
        user = db.execute("SELECT * FROM users WHERE reset_token = ?", reset_token)

        if user:
            # Reset the password and clear the reset token
            hashed_password = generate_password_hash(new_password, method='pbkdf2', salt_length=16)
            db.execute("UPDATE users SET hash = ?, reset_token = NULL WHERE id = ?", hashed_password, user[0]["id"])
            flash("Password reset successfully. You can now log in with your new password.")
            return redirect(url_for("login"))
        else:
            flash("Invalid or expired reset token.")
            return redirect(url_for("login"))

    return render_template("reset_password.html", reset_token=reset_token)
