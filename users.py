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


def get_user_data(user_id):
    return db.session.execute('''SELECT avatar_id, TO_CHAR(join_date, 'MM/YYYY') as join_date,
                                      (SELECT COUNT(*) FROM Comments WHERE user_id=:user_id) as comment_count,
                                      (SELECT COUNT(*) FROM Drinks WHERE user_id=:user_id) as recipe_count
                                      FROM Users WHERE id=:user_id''', {
        "user_id": user_id}).fetchone()


def get_user_id(username):
    try:
        return db.session.execute("SELECT id FROM Users WHERE LOWER(username)=:username", {
            "username": username.lower()}).fetchone()[0]
    except:
        return None


def logout():
    del session["username"]
    del session["user_id"]
    del session["csrf_token"]
    if "admin" in session:
        del session["admin"]


def favourited_drinks(username):
    return db.session.execute(
        '''SELECT D.id as id, D.description as description, D.name as name, D.image_id as image_id,
                COALESCE((SELECT cast(SUM(R.stars) as float) / COUNT(R.stars) FROM Ratings R WHERE R.drink_id = D.id), 0) as rating
                FROM FavouriteDrinks F
                JOIN Drinks D ON F.drink_id = D.id WHERE F.user_id = (SELECT id FROM users WHERE username=:username)
            ''', {"username": username}).fetchall()


def uploaded_drinks(username):
    return db.session.execute(
        '''SELECT D.id as id, D.description as description, D.name as name, D.image_id as image_id,
                COALESCE((SELECT cast(SUM(R.stars) as float) / COUNT(R.stars) FROM Ratings R WHERE R.drink_id = D.id), 0) as rating
                FROM Drinks D JOIN Users U on U.id = D.user_id WHERE U.username=:username
            ''', {"username": username}).fetchall()


def is_logged_user(username):
    if username != session["username"]:
        return False
    return True


def get_non_favourited_ingredients():
    user_id = session["user_id"]
    return db.session.execute(
        '''SELECT id, name, type FROM Ingredients
            WHERE id NOT IN (SELECT ingredient_id FROM UsersIngredients WHERE user_id=:user_id)
            ORDER BY name
        ''', {"user_id": user_id}).fetchall()


def get_users_ingredients():
    user_id = session["user_id"]
    return db.session.execute(
        '''SELECT U.ingredient_id as id, I.name as name FROM UsersIngredients U
            JOIN Ingredients I ON U.ingredient_id=I.id
            WHERE U.user_id=:user_id
        ''', {"user_id": user_id}).fetchall()


def add_ingredient(ingredient_id):
    try:
        user_id = session["user_id"]
        db.session.execute(
            "INSERT INTO UsersIngredients(user_id, ingredient_id) VALUES(:user_id, :ingredient_id)",
            {"user_id": user_id, "ingredient_id": ingredient_id})
        db.session.commit()
        return True
    except:
        return False


def remove_ingredient(ingredient_id):
    try:
        user_id = session["user_id"]
        db.session.execute(
            "DELETE FROM UsersIngredients WHERE ingredient_id=:ingredient_id AND user_id=:user_id",
            {"ingredient_id": ingredient_id, "user_id": user_id})
        db.session.commit()
        return True
    except:
        return False


def update_avatar(image_id):
    try:
        user_id = session["user_id"]
        previous_avatar = db.session.execute(
            "SELECT avatar_id FROM Users WHERE id=:user_id", {"user_id": user_id}).fetchone()

        db.session.execute("UPDATE Users SET avatar_id=:image_id WHERE id=:user_id", {
                           "image_id": image_id, "user_id": user_id})

        if previous_avatar:
            db.session.execute("DELETE FROM Images WHERE id=:previous_id", {
                               "previous_id": previous_avatar[0]})
        db.session.commit()
        return True
    except:
        return False


def delete_avatar(username):
    try:
        user_id = get_user_id(username)
        avatar_id = db.session.execute(
            "SELECT avatar_id FROM Users WHERE id=:user_id", {"user_id": user_id}).fetchone()
        if not avatar_id:
            return False

        db.session.execute("UPDATE Users SET avatar_id=NULL WHERE id=:user_id", {
                           "user_id": user_id})
        db.session.execute("DELETE FROM Images WHERE id=:avatar_id", {
                           "avatar_id": avatar_id[0]})

        db.session.commit()
        return True
    except:
        return False
