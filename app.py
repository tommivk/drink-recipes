from flask import Flask
from flask import render_template, request
import flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from os import getenv

app = Flask(__name__)

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
        db.session.execute(sql, {"username":username, "password_hash":hash})
        db.session.commit()

        return render_template("index.html") 
    else: 
        return render_template("signup.html") 
