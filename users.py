from db import db
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from flask import session
import secrets


def username_exists(username):
    return db.session.execute(
        "SELECT 1 FROM Users WHERE LOWER(username)=:username", {"username": username.lower()}).fetchone()


def login(username, password):
    sql = "SELECT id, username, password_hash, admin FROM users WHERE LOWER(username)=:username"
    result = db.session.execute(sql, {"username": username.lower()})
    user = result.fetchone()

    if user:
        hash = user.password_hash
        if check_password_hash(hash, password):
            session["username"] = user.username
            session["user_id"] = user.id
            session["csrf_token"] = secrets.token_hex(16)
            if user.admin == True:
                session["admin"] = True
            return True

    return False


def add_user(username, password):
    try:
        hash = generate_password_hash(password)
        sql = "INSERT INTO Users (username, password_hash, join_date, admin) VALUES(:username, :password_hash, :join_date, false)"
        db.session.execute(
            sql, {"username": username, "password_hash": hash, "join_date": datetime.now()})
        db.session.commit()
        return True
    except:
        return False


def logout():
    del session["username"]
    del session["user_id"]
    del session["csrf_token"]
    if "admin" in session:
        del session["admin"]
