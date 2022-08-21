from flask import session, request, abort

valid_units = ["cl", "ml", "tsp.", "tbsp.", "litres", "dashes", "pcs."]


def check_csrf():
    if session["csrf_token"] != request.form["csrf_token"]:
        return abort(403)


def is_logged_in():
    if "username" not in session or "user_id" not in session:
        return abort(401)
    return True


def logged_user_name():
    if "username" not in session:
        return abort(401)
    return session["username"]


def is_admin():
    if "admin" in session:
        if session["admin"] == True:
            return True
    return abort(403)
