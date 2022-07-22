from flask import Flask
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
    sql = "SELECT * FROM drinks WHERE id=:id"
    result = db.session.execute(sql, {"id": id})
    drink = result.fetchone()
    
    sql = "SELECT name FROM DrinkIngredients JOIN ingredients ON ingredients.id=DrinkIngredients.ingredient_id WHERE drink_id =:id "
    result = db.session.execute(sql, {"id": id})
    ingredients = result.fetchall()

    sql = "SELECT username FROM users WHERE id=:id"
    result = db.session.execute(sql, {"id": drink.user_id})
    author = result.fetchone()[0]
    

    return render_template("drink.html", drink=drink, ingredients=ingredients, author=author)


@app.route("/images/<int:id>")
def serve_img(id):
    sql = "SELECT data FROM images WHERE id=:id"
    result = db.session.execute(sql, {"id": id})
    data = result.fetchone()[0]
    response = make_response(bytes(data))
    response.headers.set("Content-Type", "image/jpeg")
    return response
