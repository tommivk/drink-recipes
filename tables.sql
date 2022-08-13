CREATE TABLE Images(
    id SERIAL PRIMARY KEY,
    data BYTEA
);

CREATE TABLE Users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE, 
    password_hash TEXT,
    join_date TIMESTAMP,
    avatar_id INTEGER References Images,
    admin BOOLEAN
);

CREATE TABLE DrinkCategories(
    id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT
);

CREATE TABLE Drinks (
    id SERIAL PRIMARY KEY,
    user_id integer References Users,
    name TEXT,
    description TEXT,
    recipe TEXT,
    image_id INTEGER References Images,
    category_id INTEGER References DrinkCategories,
    timestamp TIMESTAMP
);

CREATE TABLE FavouriteDrinks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER References Users,
    drink_id INTEGER References Drinks
);

CREATE TABLE Ingredients(
    id SERIAL PRIMARY KEY,
    name TEXT,
    type TEXT
);

CREATE TABLE UsersIngredients(
    id SERIAL PRIMARY KEY,
    user_id INTEGER References Users,
    ingredient_id INTEGER References Ingredients
);

CREATE TABLE DrinkIngredients(
    id SERIAL PRIMARY KEY,
    measure TEXT,
    unit TEXT,
    drink_id INTEGER References Drinks,
    ingredient_id INTEGER References Ingredients
);

CREATE TABLE Ratings(
     id SERIAL PRIMARY KEY,
     user_id INTEGER References Users,
     drink_id INTEGER References Drinks,
     stars INTEGER
);

CREATE TABLE Comments(
     id SERIAL PRIMARY KEY,
     user_id INTEGER References Users,
     drink_id INTEGER References Drinks,
     comment TEXT,
     timestamp TIMESTAMP
);
