import secrets
from datetime import datetime
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
        # TODO validate_credentials()
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
    del session["user_id"]
    del session["csrf_token"]
    return redirect("/")


@app.route("/ingredients", methods=["GET"])
def ingredients_get():
    get_logged_user()
    result = db.session.execute("SELECT name FROM ingredients")
    ingredients = result.fetchall()
    print(ingredients)
    return render_template("ingredients.html", ingredients=ingredients)


@app.route("/ingredients", methods=["POST"])
def indgredients_post():
    check_csrf()
    # TODO check if admin

    name = request.form["name"]
    type = request.form["type"]
    sql = "INSERT INTO ingredients (name, type) VALUES(:name, :type)"
    db.session.execute(sql, {"name": name, "type": type})
    db.session.commit()

    return redirect("/ingredients")


@app.route("/drinks", methods=["GET"])
def drinks_get():
    (_, user_id) = get_logged_user()
    filter_set = request.args.get(
        "owned_ingredients", default="false", type=str)

    if filter_set == "true":
        drinks = db.session.execute('''SELECT D.id, name, description, image_id,
                    COALESCE((SELECT cast(SUM(R.stars) as float) / COUNT(R.stars)
                    FROM Ratings R WHERE R.drink_id = D.id), 0) as rating
                    FROM Drinks D WHERE D.id NOT IN(SELECT DISTINCT DI.drink_id FROM DrinkIngredients DI
                    WHERE NOT EXISTS (SELECT UI.ingredient_id FROM UsersIngredients UI
                    WHERE UI.user_id=:user_id AND UI.ingredient_id IN (
                    SELECT DISTINCT DI2.ingredient_id
                    FROM DrinkIngredients DI2
                    WHERE DI2.ingredient_id=DI.ingredient_id)))''', {"user_id": user_id}).fetchall()
    else:
        drinks = db.session.execute('''SELECT id, name, description, image_id,
                                    COALESCE((SELECT cast(SUM(R.stars) as float) / COUNT(R.stars)
                                    FROM Ratings R WHERE R.drink_id = D.id), 0) as rating
                                    FROM drinks D''').fetchall()

    return render_template("drinks.html", drinks=drinks)


@app.route("/drinks", methods=["POST"])
def drinks_post():
    (_username, user_id) = get_logged_user()
    check_csrf()

    name = request.form["name"]
    recipe = request.form["recipe"]
    description = request.form["description"]
    ingredient_ids = request.form.getlist("ingredients")
    category_id = request.form["category"]
    file = request.files["picture"]

    if not file.filename.endswith(".jpg"):
        return "Invalid filetype"

    image_data = file.read()
    if len(image_data) > 200*1024:
        return "Maximum filesize is 200kB"

    sql = "INSERT INTO Images (data) VALUES(:data) RETURNING id"
    result = db.session.execute(sql, {"data": image_data})
    image_id = result.fetchone()[0]

    sql = '''INSERT INTO Drinks (user_id, name, description, recipe, image_id, category_id, timestamp)
             VALUES(:user_id, :name, :description, :recipe, :image_id, :category_id, :timestamp) RETURNING id'''
    result = db.session.execute(sql, {"user_id": user_id, "name": name, "description": description,
                                      "recipe": recipe, "image_id": image_id,
                                      "category_id": category_id, "timestamp": datetime.now()})
    drink_id = result.fetchone()[0]

    for id in ingredient_ids:
        sql = "INSERT INTO DrinkIngredients (drink_id, ingredient_id) VALUES(:drink_id, :ingredient_id)"
        db.session.execute(sql, {"drink_id": drink_id, "ingredient_id": id})

    db.session.commit()
    return redirect("/drinks")


@app.route("/drinks/add", methods=["GET"])
def new_drink_form():
    get_logged_user()
    ingredients = db.session.execute("SELECT * FROM ingredients").fetchall()
    categories = db.session.execute(
        "SELECT id, name FROM DrinkCategories").fetchall()
    return render_template("drink_form.html", ingredients=ingredients, categories=categories)


@app.route("/drinks/categories", methods=["POST"])
def add_drink_category():
    check_csrf()
    # TODO check if admin
    name = request.form["name"]
    description = request.form["description"]

    sql = "INSERT INTO DrinkCategories (name, description) VALUES(:name, :description)"
    db.session.execute(
        sql, {"name": name, "description": description})
    db.session.commit()

    return redirect("/drinks")


@app.route("/drinks/<int:id>")
def serve_drink(id):
    (_username, user_id) = get_logged_user()

    sql = '''SELECT D.id, image_id, D.name, DC.name as category, D.description, recipe, timestamp, username as author,
                (SELECT cast(SUM(R.stars) as float) / COUNT(R.stars) as rating FROM Ratings R WHERE R.drink_id = D.id),
                (SELECT Count(*) as rating_count FROM Ratings R WHERE R.drink_id = D.id),
                (SELECT (Count(*) > 0) FROM FavouriteDrinks WHERE user_id=:user_id AND drink_id=:drink_id) as is_favourited
                FROM drinks D
                JOIN Users U ON U.id = D.user_id
                JOIN DrinkCategories DC ON DC.id = D.category_id
                WHERE D.id=:drink_id
            '''
    drink = db.session.execute(
        sql, {"drink_id": id, "user_id": user_id}).fetchone()

    sql = "SELECT name FROM DrinkIngredients JOIN ingredients ON ingredients.id=DrinkIngredients.ingredient_id WHERE drink_id =:id "
    ingredients = db.session.execute(sql, {"id": id}).fetchall()

    comments = db.session.execute(
        "SELECT C.id, C.comment, TO_CHAR(C.timestamp, 'DD/MM/YYYY HH:MI') as date, username FROM Comments C JOIN Users U ON U.id = C.user_id WHERE drink_id=:drink_id ORDER BY timestamp DESC", {"drink_id": id}).fetchall()

    return render_template("drink.html", drink=drink, ingredients=ingredients, comments=comments)


@app.route("/drinks/<int:id>/comment", methods=["POST"])
def add_comment(id):
    (_username, user_id) = get_logged_user()
    check_csrf()

    comment = request.form["comment"].strip()
    if comment != "":
        sql = "INSERT INTO Comments (user_id, drink_id, comment, timestamp) VALUES(:user_id, :drink_id, :comment, :timestamp)"
        db.session.execute(sql, {"user_id": user_id, "drink_id": id,
                           "comment": comment, "timestamp": datetime.now()})
        db.session.commit()

    return redirect(f"/drinks/{id}")


@app.route("/drinks/<int:drink_id>/comment/delete", methods=["POST"])
def delete_comment(drink_id):
    (_username, user_id) = get_logged_user()
    check_csrf()

    comment_id = request.form["comment_id"]

    comment_author = db.session.execute("SELECT user_id FROM Comments WHERE id=:comment_id", {
                                        "comment_id": comment_id}).fetchone()[0]

    if user_id != comment_author:
        return abort(403)

    db.session.execute("DELETE FROM Comments WHERE id=:comment_id", {
                       "comment_id": comment_id})
    db.session.commit()

    return redirect(f"/drinks/{drink_id}")


@app.route("/drinks/<int:id>/rate", methods=["POST"])
def add_review(id):
    (_username, user_id) = get_logged_user()
    check_csrf()

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
    (_username, user_id) = get_logged_user()
    check_csrf()

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
    (username, user_id) = get_logged_user()
    check_csrf()

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
    get_logged_user()
    sql = '''SELECT D.id as id, D.description as description, D.name as name, D.image_id as image_id,
                COALESCE((SELECT cast(SUM(R.stars) as float) / COUNT(R.stars) FROM Ratings R WHERE R.drink_id = D.id), 0) as rating
                FROM FavouriteDrinks F
                JOIN drinks D ON F.drink_id = D.id WHERE F.user_id = (SELECT id FROM users WHERE username=:username)
            '''
    response = db.session.execute(sql, {"username": username})
    favourite_drinks = response.fetchall()
    return render_template("profile_page.html", username=username, favourite_drinks=favourite_drinks)


@app.route("/<string:username>/ingredients", methods=["GET"])
def user_ingredients(username):
    (user, user_id) = get_logged_user()

    if username != user:
        return abort(403)

    sql = "SELECT * FROM Ingredients WHERE id NOT IN (SELECT ingredient_id FROM UsersIngredients WHERE user_id=:user_id)"
    ingredients = db.session.execute(sql, {"user_id": user_id}).fetchall()

    sql = "SELECT * FROM UsersIngredients U JOIN Ingredients I ON U.ingredient_id=I.id WHERE U.user_id=:user_id"
    users_ingredients = db.session.execute(
        sql, {"user_id": user_id}).fetchall()

    return render_template("user_ingredients.html", ingredients=ingredients, users_ingredients=users_ingredients)


@app.route("/<string:username>/ingredients", methods=["POST"])
def favourite_ingredient(username):
    (user, user_id) = get_logged_user()
    check_csrf()

    if username != user:
        return abort(403)

    ingredient_id = request.form["ingredient"]

    sql = "INSERT INTO UsersIngredients(user_id, ingredient_id) VALUES(:user_id, :ingredient_id)"
    db.session.execute(
        sql, {"user_id": user_id, "ingredient_id": ingredient_id})
    db.session.commit()

    return redirect(f"/{username}/ingredients")


@app.route("/<string:username>/ingredients/delete", methods=["POST"])
def delete_favourite_ingredient(username):
    (user, user_id) = get_logged_user()
    check_csrf()

    if username != user:
        return abort(403)

    ingredient_id = request.form["ingredient"]

    sql = "DELETE FROM UsersIngredients WHERE ingredient_id=:ingredient_id AND user_id=:user_id"
    db.session.execute(
        sql, {"ingredient_id": ingredient_id, "user_id": user_id})
    db.session.commit()

    return redirect(f"/{username}/ingredients")


def get_logged_user():
    if "username" not in session or "user_id" not in session:
        return abort(401)
    else:
        return (session["username"], session["user_id"])


@app.errorhandler(401)
def not_logged_in(e):
    return render_template('index.html'), 401


def check_csrf():
    if session["csrf_token"] != request.form["csrf_token"]:
        return abort(403)
