from flask import session, request, abort

VALID_UNITS = ["cl", "ml", "tsp.", "tbsp.", "litres", "dashes", "pcs."]


def check_csrf():
    if session["csrf_token"] != request.form["csrf_token"]:
        return abort(403)


def check_login():
    if "username" not in session or "user_id" not in session:
        return abort(401)


def logged_user_name():
    if "username" not in session:
        return abort(401)
    return session["username"]


def is_admin():
    if "admin" in session:
        if session["admin"] == True:
            return True
    return abort(403)
