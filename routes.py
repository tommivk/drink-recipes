from db import db
from app import app
import json
import urllib
import re
from flask import abort, render_template, request, session, redirect, make_response, flash
import drinks
import users
import ratings
import ingredients
import images


@app.route("/", methods=["GET"])
def index():
    if "username" not in session:
        return redirect("/login")

    best = drinks.best()
    newest = drinks.newest()

    return render_template("index.html", best=best, newest=newest)


@app.route("/signup", methods=["GET"])
def signup_form():
    return render_template("signup.html")


@app.route("/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    password = request.form["password"]
    password_confirm = request.form["passwordConfirm"]

    if len(username) < 3 or len(username) > 20:
        flash("Username should be between 3 and 20 characters long", "error")
        return redirect("/signup")

    if password != password_confirm:
        flash("Password does not match the password confirmation", "error")
        return redirect("/signup")

    if len(password) < 6:
        flash("Password should be minimum of 6 characters long", "error")
        return redirect("/signup")

    pattern = re.compile("^[a-zA-Z0-9åäöÅÄÖ]*$")

    if not pattern.match(username):
        flash("Username contains invalid characters", "error")
        return redirect("/signup")

    username_exists = users.username_exists(username)

    if username_exists:
        flash("Username is taken", "error")
        return redirect("/signup")

    if users.add_user(username, password):
        flash("Successfully signed up")
        users.login(username, password)
        return redirect("/")
    else:
        return abort(500)


@app.route("/login", methods=["GET"])
def login():
    if "username" in session:
        return redirect("/")
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    username = request.form["username"]
    password = request.form["password"]

    if users.login(username, password):
        flash(f"Logged in as {username}")
        return redirect("/")
    else:
        flash("Invalid credentials", "error")
        return redirect("/login")


@app.route("/logout", methods=["GET"])
def logout():
    users.logout()
    return redirect("/")


@app.route("/ingredients", methods=["GET"])
def ingredients_get():
    get_logged_user()
    ingredient_names = ingredients.get_names()
    return render_template("ingredients.html", ingredients=ingredient_names)


@app.route("/ingredients", methods=["POST"])
def indgredients_post():
    is_admin()
    check_csrf()

    name = request.form["name"]
    type = request.form["type"]

    if ingredients.add_ingredient(name, type):
        flash("Ingredient added")

    return redirect(request.referrer)


@app.route("/drinks", methods=["GET"])
def drinks_get():
    (_, user_id) = get_logged_user()

    filter_set = request.args.get("filter", None)
    search = request.args.get("search", "")

    if filter_set:
        result = drinks.filtered(search)
    else:
        result = drinks.search(search)

    return render_template("drinks.html", drinks=result, search=search)


@app.route("/drinks", methods=["POST"])
def drinks_post():
    (_, user_id) = get_logged_user()
    check_csrf()

    name = request.form["name"]
    recipe = request.form["recipe"]
    description = request.form["description"]
    ingredients_data = request.form["ingredients"]
    category_id = request.form["category"]
    file = request.files["picture"]

    if not ingredients_data:
        return "Ingredients data was undefined"

    if len(name) < 3 or len(name) > 40:
        return "Name must be between 3 and 40 characters long"

    if len(description) < 5 or len(description) > 500:
        return "Description must be be between 5 and 500 characters long"

    if len(recipe) < 10 or len(recipe) > 2000:
        return "Instructions must be between 10 and 2000 characters long"

    if not file.filename.endswith(".jpg"):
        return "Invalid filetype"

    image_data = file.read()
    if len(image_data) > 200*1024:
        return "Maximum filesize is 200kB"

    result = drinks.get_category_ids()
    category_ids = [r[0] for r in result]
    if int(category_id) not in category_ids:
        return "Invalid category id"

    image_id = images.add_image(image_data)

    drink_id = drinks.add_drink(
        name, description, recipe, image_id, category_id)
    if not drink_id:
        return abort(500)

    result = ingredients.get_ids()
    ingredient_ids = [r[0] for r in result]

    ingredients_list = json.loads(urllib.parse.unquote(ingredients_data))

    for ingredient in ingredients_list:
        ingredient_id = ingredient['ingredientId']
        measure = ingredient['measure']
        unit = ingredient['unit']

        # TODO validate measure and unit

        if int(ingredient_id) not in ingredient_ids:
            return "invalid ingredient id"

        if not drinks.add_drink_ingredient(drink_id, ingredient_id, measure, unit):
            return abort(500)

    db.session.commit()

    flash(f'New recipe "{name}" created!')
    return redirect("/drinks")


@app.route("/drinks/add", methods=["GET"])
def new_drink_form():
    get_logged_user()
    all_ingredients = ingredients.get_all()
    categories = drinks.get_categories()
    return render_template("drink_form.html", ingredients=all_ingredients, categories=categories)


@app.route("/drinks/categories", methods=["POST"])
def add_drink_category():
    is_admin()
    check_csrf()

    name = request.form["name"]
    description = request.form["description"]

    if drinks.add_category(name, description):
        return redirect("/drinks")

    return abort(500)


@app.route("/drinks/<int:id>")
def serve_drink(id):
    (_, user_id) = get_logged_user()

    drink = drinks.get_by_id(id)

    if not drink:
        return abort(404)

    ingredients = drinks.get_ingredients(id)
    comments = drinks.get_comments(id)

    return render_template("drink.html", drink=drink, ingredients=ingredients, comments=comments)


@app.route("/drinks/<int:id>/delete", methods=["POST"])
def delete_drink(id):
    (username, _) = get_logged_user()
    check_csrf()

    is_author = drinks.is_author(id)

    if is_author:
        if drinks.delete_drink(id):
            flash("Drink successfully deleted")
        else:
            flash("Deleting drink failed", "error")
    else:
        return abort(403)

    return redirect(f"/users/{username}/uploaded")


@app.route("/drinks/<int:id>/comment", methods=["POST"])
def add_comment(id):
    (_, user_id) = get_logged_user()
    check_csrf()

    comment = request.form["comment"].strip()

    if comment != "":
        if drinks.add_comment(comment, id):
            flash("New comment added")
        else:
            flash("Failed to add comment", "error")

    return redirect(f"/drinks/{id}")


@app.route("/drinks/<int:drink_id>/comment/delete", methods=["POST"])
def delete_comment(drink_id):
    (_, user_id) = get_logged_user()
    check_csrf()

    comment_id = request.form["comment_id"]

    if not drinks.is_comment_author(comment_id):
        return abort(403)

    if drinks.delete_comment(comment_id):
        flash("Comment deleted")
    else:
        flash("Failed to delete comment", "error")

    return redirect(f"/drinks/{drink_id}")


@app.route("/drinks/<int:id>/rate", methods=["POST"])
def add_review(id):
    (_, user_id) = get_logged_user()
    check_csrf()

    stars = int(request.form["stars"])

    if stars not in range(1, 6):
        return "Invalid amount of stars"

    review_exists = ratings.rating_exists(id)

    if review_exists:
        if ratings.update_rating(id, stars):
            flash("Rating updated")
        else:
            return abort(500)
    else:
        if ratings.add_rating(id, stars):
            flash("Rating added")
        else:
            return abort(500)

    return redirect(f"/drinks/{id}")


@app.route("/drinks/<int:id>/favourite", methods=["POST"])
def favourite_drink(id):
    (_, user_id) = get_logged_user()
    check_csrf()

    is_favourited = drinks.is_favourited(id)

    if is_favourited:
        return "Error"
    else:
        if drinks.add_favourite(id):
            flash("Recipe added to favourites")
        else:
            return abort(500)
    return redirect(f"/drinks/{id}")


@app.route("/drinks/<int:id>/favourite/delete", methods=["POST"])
def favourite_drink_delete(id):
    (username, user_id) = get_logged_user()
    check_csrf()

    is_favourited = drinks.is_favourited(id)

    if is_favourited:
        if drinks.delete_favourite(id):
            drink = drinks.get_name(id)
            flash(f"{drink} removed from favourites")
            return redirect(request.referrer)
        else:
            return abort(500)
    else:
        return abort(403)


@app.route("/images/<int:id>")
def serve_img(id):
    data = images.get_image(id)
    if not data:
        return abort(404)
    response = make_response(bytes(data[0]))
    response.headers.set("Content-Type", "image/jpeg")
    return response


@app.route("/users/<string:username>")
def profile_page(username):
    get_logged_user()
    user_id = users.get_user_id(username)
    if not user_id:
        return abort(404)

    user_data = users.get_user_data(user_id)
    return render_template("user_profile.html", user_data=user_data, username=username)


@app.route("/users/<string:username>/ingredients", methods=["GET"])
def user_ingredients(username):
    (user, user_id) = get_logged_user()

    if username != user:
        return abort(403)

    ingredients = users.get_non_favourited_ingredients()
    users_ingredients = users.get_users_ingredients()

    return render_template("user_ingredients.html", username=username, ingredients=ingredients, users_ingredients=users_ingredients)


@app.route("/users/<string:username>/ingredients", methods=["POST"])
def favourite_ingredient(username):
    (user, user_id) = get_logged_user()
    check_csrf()

    if username != user:
        return abort(403)

    ingredient_id = request.form["ingredient"]

    if users.add_ingredient(ingredient_id):
        flash("Ingredient added")

    return redirect(f"/users/{username}/ingredients")


@app.route("/users/<string:username>/uploaded", methods=["GET"])
def user_uploaded(username):
    get_logged_user()

    uploaded_drinks = users.uploaded_drinks(username)

    return render_template("user_uploaded.html", username=username, uploaded_drinks=uploaded_drinks)


@app.route("/users/<string:username>/favourited", methods=["GET"])
def user_favourited(username):
    (user, _) = get_logged_user()

    if not users.is_logged_user(username):
        return abort(403)

    favourited_drinks = users.favourited_drinks(username)

    return render_template("user_favourited.html", username=username, favourited_drinks=favourited_drinks)


@app.route("/users/<string:username>/ingredients/delete", methods=["POST"])
def delete_favourite_ingredient(username):
    (user, user_id) = get_logged_user()
    check_csrf()

    if not users.is_logged_user(username):
        return abort(403)

    ingredient_id = request.form["ingredient"]

    if users.remove_ingredient(ingredient_id):
        flash("Ingredient removed")

    return redirect(f"/users/{username}/ingredients")


@app.route("/admin", methods=["GET"])
def admin_panel():
    is_admin()
    return render_template("admin.html")


def get_logged_user():
    if "username" not in session or "user_id" not in session:
        return abort(401)
    else:
        return (session["username"], session["user_id"])


# @app.errorhandler(401)
# def not_logged_in(e):
#     return render_template('index.html'), 401


def check_csrf():
    if session["csrf_token"] != request.form["csrf_token"]:
        return abort(403)


def is_admin():
    if "admin" in session:
        if session["admin"] == True:
            return
    return abort(403)
