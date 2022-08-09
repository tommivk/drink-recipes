from app import app
from os import getenv
from flask_sqlalchemy import SQLAlchemy

DATABASE_URL = getenv('DATABASE_URL')
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
db = SQLAlchemy(app)
