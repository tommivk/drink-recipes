from db import db


def get_all():
    return db.session.execute(
        "SELECT * FROM ingredients ORDER BY name").fetchall()


def get_names():
    return db.session.execute("SELECT name FROM ingredients").fetchall()


def add_ingredient(name, type):
    try:
        sql = "INSERT INTO ingredients (name, type) VALUES(:name, :type)"
        db.session.execute(sql, {"name": name, "type": type})
        db.session.commit()
        return True
    except:
        return False


def get_ids():
    return db.session.execute("SELECT id FROM ingredients").fetchall()


def ingredient_exists(name):
    return db.session.execute("SELECT 1 FROM Ingredients WHERE LOWER(name)=:name",
                              {"name": name.lower()}).fetchone()
