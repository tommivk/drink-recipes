from db import db


def get_all():
    return db.session.execute(
        "SELECT id, name, type FROM Ingredients ORDER BY name").fetchall()


def get_names():
    return db.session.execute("SELECT name FROM Ingredients").fetchall()


def add_ingredient(name, type):
    try:
        sql = "INSERT INTO Ingredients (name, type) VALUES(:name, :type)"
        db.session.execute(sql, {"name": name, "type": type})
        db.session.commit()
        return True
    except:
        return False


def get_ids():
    return db.session.execute("SELECT id FROM Ingredients").fetchall()


def ingredient_exists(name):
    return db.session.execute("SELECT 1 FROM Ingredients WHERE LOWER(name)=:name",
                              {"name": name.lower()}).fetchone()


def get_by_id(id):
    return db.session.execute("SELECT id, name, type FROM Ingredients WHERE id=:id",
                              {"id": id}).fetchone()
