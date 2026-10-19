import math
import os
from datetime import date

import certifi
import frontend_app as frontend
from dotenv import load_dotenv
from flask import Flask, redirect, request, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

app = Flask(__name__)

mongo_uri = os.getenv("MONGO_URI")
database_name = os.getenv("MONGO_DBNAME")

if not mongo_uri or not database_name:
    raise RuntimeError(
        "Missing MONGO_URI or MONGO_DBNAME in .env"
    )

client = MongoClient(
    mongo_uri,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=10000
)

db = client[database_name]
food_entries = db["food_entries"]

MEAL_CHOICES = (
    ("breakfast", "Breakfast"),
    ("lunch", "Lunch"),
    ("dinner", "Dinner"),
    ("snacks", "Snacks"),
)
NUTRIENT_LABELS = {
    "calories": "Calories",
    "protein": "Protein",
    "carbs": "Carbohydrates",
    "fat": "Fat",
}


def validate_food_entry(form):
    """Build the food document from supported, validated fields only."""
    entry = {
        "date": form.get("date", "").strip(),
        "food_name": form.get("food_name", "").strip(),
        "meal": form.get("meal", "").strip(),
    }
    errors = []

    if not entry["food_name"]:
        errors.append("Please enter a food name.")

    try:
        parsed_date = date.fromisoformat(entry["date"])
        if parsed_date.isoformat() != entry["date"]:
            raise ValueError
    except ValueError:
        errors.append("Please enter a valid date in YYYY-MM-DD format.")

    if entry["meal"] not in dict(MEAL_CHOICES):
        errors.append("Please choose breakfast, lunch, dinner, or snacks.")

    for field, label in NUTRIENT_LABELS.items():
        try:
            value = float(form.get(field, ""))
        except ValueError:
            errors.append(f"Please enter a number for {label.lower()}.")
            continue

        if not math.isfinite(value) or value < 0:
            errors.append(f"{label} must be a valid number of 0 or more.")
        else:
            entry[field] = value

    return entry, errors


@app.route("/")
def home():
    return frontend.index()


# Reuse the team's UI. Other screens retain their sample-data preview until
# their respective backend features are connected.
app.add_url_rule("/", endpoint="index", view_func=home)
app.add_url_rule("/meals", endpoint="meals", view_func=frontend.meals)
app.add_url_rule("/search", endpoint="search", view_func=frontend.search)
app.add_url_rule("/goals", endpoint="goals", view_func=frontend.goals)
app.add_url_rule(
    "/meals/<meal_id>/edit", endpoint="edit_meal", view_func=frontend.edit_meal
)
app.add_url_rule(
    "/meals/<meal_id>/delete", endpoint="delete_meal", view_func=frontend.delete_meal
)


@app.route("/db-test")
def db_test():
    client.admin.command("ping")
    return "Successfully connected to MongoDB!"


@app.route("/add", methods=["GET", "POST"])
@app.route("/meals/new", methods=["GET", "POST"], endpoint="add_meal")
def add_food_entry():
    errors = []
    status_code = 200

    if request.method == "POST":
        entry, errors = validate_food_entry(request.form)
        if errors:
            status_code = 400
        else:
            try:
                food_entries.insert_one(entry)
            except PyMongoError as error:
                app.logger.warning("Food entry save failed: %s", type(error).__name__)
                errors.append(
                    "We couldn't confirm that your entry was saved. "
                    "Please check before submitting again."
                )
                status_code = 503
            else:
                # A fresh GET after saving prevents refresh from repeating the POST.
                return redirect(url_for("add_meal", saved="1"), code=303)

    return frontend.screen(
        "add_food_entry.html",
        "Add Food Entry",
        subtitle="Record a meal and its nutrition information",
        preview=False,
        errors=errors,
        meal_choices=MEAL_CHOICES,
        today=date.today().isoformat() if request.method == "GET" else "",
        saved=request.method == "GET" and request.args.get("saved") == "1",
    ), status_code


if __name__ == "__main__":
    app.run(debug=True)
