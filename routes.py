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
from werkzeug.exceptions import HTTPException
from util import is_admin, logged_user_name, check_csrf, VALID_UNITS, check_login


@app.errorhandler(HTTPException)
def http_error(e):
    if e.code == 401:
        return redirect("/login")
    return render_template("error.html", error_code=e.code, error_msg=e.description)


@app.route("/", methods=["GET"])
def index():
    check_login()

    best = drinks.best()
    newest = drinks.newest()
    most_viewed = drinks.most_viewed()

    return render_template("index.html", best=best, newest=newest, most_viewed=most_viewed)


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
    check_login()
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
    check_login()

    filter_set = request.args.get("filter", None)
    search = request.args.get("search", "")

    if filter_set:
        result = drinks.filtered(search)
    else:
        result = drinks.search(search)

    return render_template("drinks.html", drinks=result, search=search)


@app.route("/drinks", methods=["POST"])
def drinks_post():
    check_login()
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

    filename = file.filename
    if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
        return "Invalid filetype"

    image_data = file.read()
    if len(image_data) > 200*1024:
        return "Maximum filesize is 200kB"

    result = drinks.get_category_ids()
    category_ids = [r[0] for r in result]
    if int(category_id) not in category_ids:
        return "Invalid category id"

    image_id = images.add_image(image_data)
    if not image_id:
        return abort(500)

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

        if unit and not measure:
            return "Measure cannot be empty if unit is selected"

        if measure and not unit:
            return "Unit cannot be empty id measure is selected"

        if measure and not (measure.replace(".", "", 1).isdigit()):
            return "Invalid measure"

        if measure and float(measure) < 0:
            return "Measure cannot be negative"

        if unit and unit not in VALID_UNITS:
            return "Invalid unit"

        if int(ingredient_id) not in ingredient_ids:
            return "invalid ingredient id"

        if not drinks.add_drink_ingredient(drink_id, ingredient_id, measure, unit):
            return abort(500)

    db.session.commit()

    flash(f'New recipe "{name}" created!')
    return redirect("/drinks")


@app.route("/drinks/add", methods=["GET"])
def new_drink_form():
    check_login()
    all_ingredients = ingredients.get_all()
    categories = drinks.get_categories()
    units = VALID_UNITS
    return render_template("drink_form.html", ingredients=all_ingredients, categories=categories, units=units)


@app.route("/drinks/categories", methods=["POST"])
def add_drink_category():
    is_admin()
    check_csrf()

    name = request.form["name"]
    description = request.form["description"]

    if drinks.add_category(name, description):
        return redirect("/drinks")

    return abort(500)


@app.route("/drinks/<int:id>", methods=["GET"])
def serve_drink(id):
    check_login()

    drink = drinks.get_by_id(id)

    if not drink:
        return abort(404)

    drinks.add_view(id)

    ingredients = drinks.get_ingredients(id)
    comments = drinks.get_comments(id)

    return render_template("drink.html", drink=drink, ingredients=ingredients, comments=comments)


@app.route("/drinks/<int:id>/delete", methods=["POST"])
def delete_drink(id):
    check_login()
    check_csrf()

    allow = (drinks.is_author(id) or is_admin())

    if allow:
        if drinks.delete_drink(id):
            flash("Drink successfully deleted")
        else:
            flash("Deleting drink failed", "error")
    else:
        return abort(403)

    username = logged_user_name()
    return redirect(f"/users/{username}/uploaded")


@app.route("/drinks/<int:id>/comment", methods=["POST"])
def add_comment(id):
    check_login()
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
    check_login()
    check_csrf()

    comment_id = request.form["comment_id"]

    if not (drinks.is_comment_author(comment_id) or is_admin()):
        return abort(403)

    if drinks.delete_comment(comment_id):
        flash("Comment deleted")
    else:
        flash("Failed to delete comment", "error")

    return redirect(f"/drinks/{drink_id}")


@app.route("/drinks/<int:id>/rate", methods=["POST"])
def add_review(id):
    check_login()
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
    check_login()
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
    check_login()
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
    check_login()
    user_id = users.get_user_id(username)
    if not user_id:
        return abort(404)

    user_data = users.get_user_data(user_id)

    return render_template("user_profile.html", user_data=user_data, username=username)


@app.route("/users/<string:username>/update", methods=["POST"])
def update_profile(username):
    check_login()
    check_csrf()
    user = logged_user_name()

    if username != user:
        return abort(403)

    file = request.files["picture"]

    image_data = file.read()

    filename = file.filename
    if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
        return "Invalid filetype"

    if len(image_data) > 200*1024:
        return "Maximum filesize is 200kB"

    image_id = images.add_image(image_data)

    if not image_id:
        return abort(500)

    if users.update_avatar(image_id):
        flash("Profile updated")

    return redirect(request.referrer)


@app.route("/users/<string:username>/ingredients", methods=["GET"])
def user_ingredients(username):
    check_login()
    user = logged_user_name()

    if username != user:
        return abort(403)

    ingredients = users.get_non_favourited_ingredients()
    users_ingredients = users.get_users_ingredients()

    return render_template("user_ingredients.html", username=username, ingredients=ingredients, users_ingredients=users_ingredients)


@app.route("/users/<string:username>/ingredients", methods=["POST"])
def favourite_ingredient(username):
    check_login()
    check_csrf()

    if not users.is_logged_user(username):
        return abort(403)

    ingredient_id = request.form["ingredient"]

    if users.add_ingredient(ingredient_id):
        flash("Ingredient added")

    return redirect(f"/users/{username}/ingredients")


@app.route("/users/<string:username>/uploaded", methods=["GET"])
def user_uploaded(username):
    check_login()

    uploaded_drinks = users.uploaded_drinks(username)

    return render_template("user_uploaded.html", username=username, uploaded_drinks=uploaded_drinks)


@app.route("/users/<string:username>/favourited", methods=["GET"])
def user_favourited(username):
    check_login()

    if not users.is_logged_user(username):
        return abort(403)

    favourited_drinks = users.favourited_drinks(username)

    return render_template("user_favourited.html", username=username, favourited_drinks=favourited_drinks)


@app.route("/users/<string:username>/avatar/delete", methods=["POST"])
def delete_avatar(username):
    check_login()
    check_csrf()

    if not (users.is_logged_user(username) or is_admin()):
        return abort(403)

    if users.delete_avatar(username):
        flash("Avatar deleted")
    else:
        return abort(500)

    return redirect(request.referrer)


@app.route("/users/<string:username>/ingredients/delete", methods=["POST"])
def delete_favourite_ingredient(username):
    check_login()
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
