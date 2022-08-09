from db import db
from flask import session


def update_rating(drink_id, stars):
    try:
        user_id = session["user_id"]
        db.session.execute(
            "UPDATE ratings SET stars=:stars WHERE user_id=:user_id AND drink_id=:drink_id",
            {"user_id": user_id, "drink_id": drink_id, "stars": stars})
        db.session.commit()
        return True
    except:
        return False


def add_rating(drink_id, stars):
    try:
        user_id = session["user_id"]
        db.session.execute(
            "INSERT INTO ratings (user_id, drink_id, stars) VALUES(:user_id, :drink_id, :stars)",
            {"user_id": user_id, "drink_id": drink_id, "stars": stars})
        db.session.commit()
        return True
    except:
        return False


def rating_exists(drink_id):
    user_id = session["user_id"]
    return db.session.execute("SELECT 1 FROM ratings WHERE user_id=:user_id AND drink_id=:drink_id", {
        "user_id": user_id, "drink_id": drink_id}).fetchone()
