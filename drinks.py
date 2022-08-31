from db import db
from flask import session
from datetime import datetime


def best():
    return db.session.execute(
        '''SELECT D.id, D.name, D.description, D.image_id, CAST(SUM(R.stars) as float) / COUNT(R.stars) as rating
           FROM Drinks D
           JOIN Ratings R ON D.id=R.drink_id
           GROUP BY D.id
           ORDER BY rating DESC, COUNT(R.id) DESC LIMIT 5
           ''').fetchall()


def newest():
    return db.session.execute(
        '''SELECT  D.id, D.name, D.description, D.image_id, COALESCE(CAST(SUM(R.stars) as float) / COUNT(R.stars), 0) as rating
           FROM Drinks D
           LEFT JOIN Ratings R ON D.id=R.drink_id
           GROUP BY D.id
           ORDER BY timestamp DESC LIMIT 4''').fetchall()


def most_viewed():
    return db.session.execute('''SELECT D.id, D.name, D.views, D.description, D.image_id, CAST(SUM(R.stars) as float) / COUNT(R.stars) as rating
           FROM Drinks D
           LEFT JOIN Ratings R ON D.id=R.drink_id
           GROUP BY D.id
           ORDER BY D.views DESC LIMIT 5''').fetchall()


def filtered(search):
    user_id = session["user_id"]
    return db.session.execute(
        '''SELECT D.id, name, description, image_id,
                    COALESCE((SELECT cast(SUM(R.stars) as float) / COUNT(R.stars)
                    FROM Ratings R WHERE R.drink_id = D.id), 0) as rating
                    FROM Drinks D WHERE D.id NOT IN(SELECT DISTINCT DI.drink_id FROM DrinkIngredients DI
                    WHERE NOT EXISTS (SELECT UI.ingredient_id FROM UsersIngredients UI
                    WHERE UI.user_id=:user_id AND UI.ingredient_id IN (
                    SELECT DISTINCT DI2.ingredient_id
                    FROM DrinkIngredients DI2
                    WHERE DI2.ingredient_id=DI.ingredient_id AND LOWER(name) LIKE :search)))
                    ORDER BY timestamp DESC''',
        {"user_id": user_id, "search": f"%{search.lower()}%"}).fetchall()


def search(search):
    return db.session.execute('''SELECT id, name, description, image_id,
                                    COALESCE((SELECT cast(SUM(R.stars) as float) / COUNT(R.stars)
                                    FROM Ratings R WHERE R.drink_id = D.id), 0) as rating
                                    FROM drinks D WHERE LOWER(name) LIKE :search
                                    ORDER BY timestamp DESC''',
                              {"search": f"%{search.lower()}%"}).fetchall()


def add_category(name, description):
    try:
        sql = "INSERT INTO DrinkCategories (name, description) VALUES(:name, :description)"
        db.session.execute(
            sql, {"name": name, "description": description})
        db.session.commit()
        return True
    except:
        return False


def get_categories():
    return db.session.execute(
        "SELECT id, name FROM DrinkCategories").fetchall()


def category_exists(name):
    return db.session.execute("SELECT 1 FROM DrinkCategories WHERE LOWER(name)=:name", {"name": name.lower()}).fetchone()


def get_category_ids():
    return db.session.execute("SELECT id FROM DrinkCategories").fetchall()


def get_by_id(id):
    try:
        user_id = session["user_id"]
        return db.session.execute(
            '''SELECT D.id, image_id, D.name, DC.name as category, D.description, recipe, timestamp, username as author,
                    COALESCE((SELECT cast(SUM(R.stars) as float) / COUNT(R.stars) FROM Ratings R WHERE R.drink_id = D.id), 0) as rating,
                    (SELECT Count(*) as rating_count FROM Ratings R WHERE R.drink_id = D.id),
                    (SELECT (Count(*) > 0) FROM FavouriteDrinks WHERE user_id=:user_id AND drink_id=:drink_id) as is_favourited
                    FROM drinks D
                    JOIN Users U ON U.id = D.user_id
                    JOIN DrinkCategories DC ON DC.id = D.category_id
                    WHERE D.id=:drink_id
                ''', {"drink_id": id, "user_id": user_id}).fetchone()
    except:
        return None


def get_ingredients(id):
    return db.session.execute('''SELECT name, unit, measure
                                    FROM DrinkIngredients
                                    JOIN ingredients ON ingredients.id=DrinkIngredients.ingredient_id
                                    WHERE drink_id =:id
                                ''', {"id": id}).fetchall()


def get_comments(id):
    return db.session.execute(
        '''SELECT C.id, C.comment, TO_CHAR(C.timestamp, 'DD/MM/YYYY HH24:MI') as date, U.username, U.avatar_id,
            COALESCE((SELECT stars FROM Ratings R WHERE R.drink_id=:drink_id AND R.user_id = U.id), 0) as rating
            FROM Comments C
            JOIN Users U ON U.id = C.user_id
            WHERE C.drink_id=:drink_id
            ORDER BY timestamp DESC
            ''',
        {"drink_id": id}).fetchall()


def get_name(id):
    return db.session.execute(
        "SELECT name FROM Drinks where id=:id", {"id": id}).fetchone()[0]


def add_drink(name, description, recipe, image_id, category_id):
    try:
        user_id = session["user_id"]
        sql = '''INSERT INTO Drinks (user_id, name, description, recipe, image_id, category_id, timestamp)
                 VALUES(:user_id, :name, :description, :recipe, :image_id, :category_id, :timestamp) RETURNING id'''
        result = db.session.execute(sql, {"user_id": user_id, "name": name, "description": description,
                                          "recipe": recipe, "image_id": image_id,
                                          "category_id": category_id, "timestamp": datetime.now()})
        drink_id = result.fetchone()[0]
        return drink_id
    except:
        return None


def add_drink_ingredient(drink_id, ingredient_id, measure, unit):
    try:
        sql = "INSERT INTO DrinkIngredients (drink_id, ingredient_id, measure, unit) VALUES(:drink_id, :ingredient_id, :measure, :unit)"
        db.session.execute(
            sql, {"drink_id": drink_id, "ingredient_id": ingredient_id, "measure": measure, "unit": unit})
        return True
    except:
        return False


def add_comment(comment, drink_id):
    try:
        user_id = session["user_id"]
        sql = "INSERT INTO Comments (user_id, drink_id, comment, timestamp) VALUES(:user_id, :drink_id, :comment, :timestamp)"
        db.session.execute(sql, {"user_id": user_id, "drink_id": drink_id,
                                 "comment": comment, "timestamp": datetime.now()})
        db.session.commit()
        return True
    except:
        return False


def add_favourite(id):
    try:
        user_id = session["user_id"]
        sql = "INSERT INTO FavouriteDrinks (user_id, drink_id) VALUES(:user_id, :drink_id)"
        db.session.execute(sql, {"user_id": user_id, "drink_id": id})
        db.session.commit()
        return True
    except:
        return False


def is_comment_author(comment_id):
    user_id = session["user_id"]
    return db.session.execute("SELECT 1 FROM Comments WHERE id=:comment_id AND user_id=:user_id", {
        "comment_id": comment_id, "user_id": user_id}).fetchone()


def is_author(drink_id):
    user_id = session["user_id"]
    return db.session.execute("SELECT 1 FROM Drinks WHERE id=:id AND user_id=:user_id", {
        "id": drink_id, "user_id": user_id}).fetchone()


def is_favourited(id):
    user_id = session["user_id"]
    return db.session.execute("SELECT 1 FROM FavouriteDrinks WHERE user_id=:user_id AND drink_id=:drink_id", {
        "user_id": user_id, "drink_id": id}).fetchone()


def delete_comment(comment_id):
    try:
        db.session.execute("DELETE FROM Comments WHERE id=:comment_id", {
                           "comment_id": comment_id})
        db.session.commit()
        return True
    except:
        return False


def delete_favourite(id):
    try:
        user_id = session["user_id"]
        db.session.execute("DELETE FROM FavouriteDrinks WHERE drink_id=:drink_id AND user_id=:user_id", {
                           "user_id": user_id, "drink_id": id})
        db.session.commit()
        return True
    except:
        return False


def delete_drink(id):
    try:
        image_id = db.session.execute(
            "SELECT image_id FROM Drinks WHERE id=:id", {"id": id}).fetchone()[0]
        db.session.execute(
            "DELETE FROM Comments WHERE drink_id=:id", {"id": id})
        db.session.execute(
            "DELETE FROM Ratings WHERE drink_id=:id", {"id": id})
        db.session.execute(
            "DELETE FROM DrinkIngredients WHERE drink_id=:id", {"id": id})
        db.session.execute(
            "DELETE FROM FavouriteDrinks WHERE drink_id=:id", {"id": id})
        db.session.execute("DELETE FROM Drinks WHERE id=:id", {"id": id})
        db.session.execute(
            "DELETE FROM Images WHERE id=:image_id", {"image_id": image_id})
        db.session.commit()
        return True
    except:
        return False


def add_view(id):
    try:
        db.session.execute(
            "UPDATE Drinks SET views = views + 1 WHERE id=:id", {"id": id})
        db.session.commit()
        return True
    except:
        return False
