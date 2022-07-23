import secrets
from flask import Flask, abort
from flask import render_template, request, session, redirect, make_response
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
            session["user_id"] = user.id
            session["csrf_token"] = secrets.token_hex(16)
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
    check_csrf()

    name = request.form["name"]
    type = request.form["type"]
    sql = "INSERT INTO ingredients (name, type) VALUES(:name, :type)"
    db.session.execute(sql, {"name": name, "type": type})
    db.session.commit()

    return redirect("/ingredients")


@app.route("/drinks", methods=["GET"])
def drinks_get():
    result = db.session.execute(
        "SELECT id, name, image_id FROM drinks")
    drinks = result.fetchall()
    result = db.session.execute("SELECT * FROM ingredients")
    ingredients = result.fetchall()
    return render_template("drinks.html", drinks=drinks, ingredients=ingredients)


@app.route("/drinks", methods=["POST"])
def drinks_post():
    check_csrf()

    if "username" in session:
        user = session["username"]
    else:
        return redirect("/")

    name = request.form["name"]
    recipe = request.form["recipe"]
    description = request.form["description"]
    ingredient_ids = request.form.getlist("ingredients")
    file = request.files["picture"]

    if not file.filename.endswith(".jpg"):
        return "Invalid filetype"

    image_data = file.read()
    if len(image_data) > 200*1024:
        return "Maximum filesize is 200kB"

    sql = "SELECT id FROM users WHERE username=:user"
    result = db.session.execute(sql, {"user": user})
    user_id = result.fetchone()[0]

    sql = "INSERT INTO Images (data) VALUES(:data) RETURNING id"
    result = db.session.execute(sql, {"data": image_data})
    image_id = result.fetchone()[0]

    sql = "INSERT INTO Drinks (user_id, name, description, recipe, image_id) VALUES(:user_id, :name, :description, :recipe, :image_id) RETURNING id"
    result = db.session.execute(sql, {"user_id": user_id, "name": name,
                                "description": description, "recipe": recipe, "image_id": image_id})
    drink_id = result.fetchone()[0]

    for id in ingredient_ids:
        sql = "INSERT INTO DrinkIngredients (drink_id, ingredient_id) VALUES(:drink_id, :ingredient_id)"
        db.session.execute(sql, {"drink_id": drink_id, "ingredient_id": id})

    db.session.commit()
    return redirect("/drinks")


@app.route("/drinks/<int:id>")
def serve_drink(id):
    if "user_id" in session:
        user_id = session["user_id"]

    sql = "SELECT *, (SELECT (Count(*) > 0) FROM FavouriteDrinks WHERE user_id=:user_id AND drink_id=:drink_id) as is_favourited FROM drinks WHERE id=:drink_id"
    result = db.session.execute(sql, {"drink_id": id, "user_id": user_id})
    drink = result.fetchone()

    sql = "SELECT name FROM DrinkIngredients JOIN ingredients ON ingredients.id=DrinkIngredients.ingredient_id WHERE drink_id =:id "
    result = db.session.execute(sql, {"id": id})
    ingredients = result.fetchall()

    sql = "SELECT username FROM users WHERE id=:author_id"
    result = db.session.execute(sql, {"author_id": drink.user_id})
    author = result.fetchone()[0]

    sql = "SELECT (cast(SUM(stars) as float) / COUNT(stars)) as rating, Count(*) as rating_count FROM Ratings WHERE drink_id=:drink_id"
    result = db.session.execute(sql, {"drink_id": drink.id})
    rating_data = result.fetchone()

    return render_template("drink.html", drink=drink, ingredients=ingredients, author=author, rating_data=rating_data)


@app.route("/drinks/<int:id>/rate", methods=["POST"])
def add_review(id):
    check_csrf()

    if "user_id" in session:
        user_id = session["user_id"]
    else:
        redirect("/")

    stars = int(request.form["stars"])

    sql = "SELECT COUNT(*) FROM ratings WHERE user_id=:user_id AND drink_id=:drink_id"
    result = db.session.execute(sql, {"user_id": user_id, "drink_id": id})
    review_exists = int(result.fetchone()[0]) > 0

    if stars not in range(1, 6):
        return "Invalid amount of stars"

    if review_exists:
        sql = "UPDATE ratings SET stars=:stars WHERE user_id=:user_id AND drink_id=:drink_id"
    else:
        sql = "INSERT INTO ratings (user_id, drink_id, stars) VALUES(:user_id, :drink_id, :stars)"

    db.session.execute(
        sql, {"user_id": user_id, "drink_id": id, "stars": stars})
    db.session.commit()

    return redirect(f"/drinks/{id}")


@app.route("/drinks/<int:id>/favourite", methods=["POST"])
def favourite_drink(id):
    check_csrf()

    if "user_id" in session:
        user_id = session["user_id"]
    else:
        redirect("/")

    sql = "SELECT COUNT(*) FROM FavouriteDrinks WHERE user_id=:user_id AND drink_id=:drink_id"
    result = db.session.execute(sql, {"user_id": user_id, "drink_id": id})

    is_favourited = result.fetchone()[0] > 0

    if is_favourited:
        return "Error"
    else:
        sql = "INSERT INTO FavouriteDrinks (user_id, drink_id) VALUES(:user_id, :drink_id)"
        db.session.execute(sql, {"user_id": user_id, "drink_id": id})
        db.session.commit()

    return redirect(f"/drinks/{id}")


@app.route("/drinks/<int:id>/favourite/delete", methods=["POST"])
def favourite_drink_delete(id):
    check_csrf()
    if "user_id" in session:
        user_id = session["user_id"]
    else:
        redirect("/")

    username = session["username"]

    sql = "DELETE FROM FavouriteDrinks WHERE drink_id=:drink_id AND user_id=:user_id"
    db.session.execute(sql, {"user_id": user_id, "drink_id": id})
    db.session.commit()

    return redirect(f"/{username}")


@app.route("/images/<int:id>")
def serve_img(id):
    sql = "SELECT data FROM images WHERE id=:id"
    result = db.session.execute(sql, {"id": id})
    data = result.fetchone()[0]
    response = make_response(bytes(data))
    response.headers.set("Content-Type", "image/jpeg")
    return response


@app.route("/<string:username>")
def profile_page(username):
    sql = "SELECT D.id as id, D.name as name, D.image_id as image_id FROM FavouriteDrinks F JOIN drinks D ON F.drink_id = D.id WHERE F.user_id = (SELECT id FROM users WHERE username=:username)"
    response = db.session.execute(sql, {"username": username})
    favourite_drinks = response.fetchall()
    return render_template("profile_page.html", username=username, favourite_drinks=favourite_drinks)


def check_csrf():
    if session["csrf_token"] != request.form["csrf_token"]:
        return abort(403)
