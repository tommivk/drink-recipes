from flask import Flask
from flask import render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from os import getenv

app = Flask(__name__)
app.secret_key = getenv("SECRET_KEY")

DATABASE_URI = getenv('DATABASE_URI')
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
db = SQLAlchemy(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hash = generate_password_hash(password)
        sql = "INSERT INTO Users (username, password_hash) VALUES(:username, :password_hash)"
        db.session.execute(sql, {"username": username, "password_hash": hash})
        db.session.commit()

        return render_template("index.html")
    else:
        return render_template("signup.html")


@app.route("/login", methods=["GET"])
def login_form():
    return render_template("login_form.html")


@app.route("/login", methods=["POST"])
def login_post():
    username = request.form["username"]
    password = request.form["password"]

    sql = "SELECT id, password_hash FROM users WHERE username=:username"
    result = db.session.execute(sql, {"username": username})
    user = result.fetchone()

    if not user:
        return "Invalid username"
    else:
        hash = user.password_hash

        if check_password_hash(hash, password):
            session["username"] = username
            return redirect("/")
        else:
            return "Invalid password"


@app.route("/logout")
def logout():
    del session["username"]
    return redirect("/")


@app.route("/ingredients", methods=["GET"])
def ingredients_get():
    result = db.session.execute("SELECT name FROM ingredients")
    ingredients = result.fetchall()
    print(ingredients)
    return render_template("ingredients.html", ingredients=ingredients)


@app.route("/ingredients", methods=["POST"])
def indgredients_post():
    name = request.form["name"]
    type = request.form["type"]
    sql = "INSERT INTO ingredients (name, type) VALUES(:name, :type)"
    db.session.execute(sql, {"name": name, "type": type})
    db.session.commit()

    return redirect("/ingredients")
