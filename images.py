from db import db


def add_image(image_data):
    try:
        sql = "INSERT INTO Images (data) VALUES(:data) RETURNING id"
        result = db.session.execute(sql, {"data": image_data})
        image_id = result.fetchone()[0]
        return image_id
    except:
        return None


def get_image(id):
    return db.session.execute("SELECT data FROM Images WHERE id=:id", {"id": id}).fetchone()
