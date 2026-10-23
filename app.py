import math
import os
import secrets
import hmac
from datetime import date

import certifi
import frontend_app as frontend
from dotenv import load_dotenv
from flask import Flask, redirect, request, url_for, session, abort, flash, get_flashed_messages
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from bson.errors import InvalidId

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

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
    "/meals/<meal_id>/delete", endpoint="delete_meal", view_func=frontend.delete_meal
)


@app.route("/entries")
def saved_entries():
    """Small real-data editing entry point while team history is integrated."""
    page = request.args.get("page", 1, type=int)
    page = max(1, min(page or 1, 10000))
    try:
        entries = list(food_entries.find().sort([("date", -1), ("_id", -1)])
                       .skip((page - 1) * 50).limit(51))
    except PyMongoError:
        return frontend.screen("saved_entries.html", "Saved entries", preview=False,
                               entries=[], error="Saved entries are unavailable. Please try again.",
                               page=page, has_next=False), 503
    return frontend.screen("saved_entries.html", "Saved entries", preview=False,
                           entries=entries[:50], error=None, page=page,
                           has_next=len(entries) > 50)

@app.route("meals/<meal_id>/delete", methods=["POST"])
def delete_meal(meal_id):
    

@app.route("/meals/<meal_id>/edit", methods=["GET", "POST"])
def edit_meal(meal_id):
    if not ObjectId.is_valid(meal_id):
        # Keep the existing explicitly labeled sample screens usable.
        if request.method == "GET" and any(meal["id"] == meal_id for meal in frontend.sample_meals()):
            return frontend.edit_meal(meal_id)
        abort(404)
    entry_id = ObjectId(meal_id)
    token = session.setdefault("edit_csrf", secrets.token_hex(32))
    errors = []
    status = 200
    values = request.form if request.method == "POST" else {}
    if request.method == "POST" and not hmac.compare_digest(
        request.form.get("csrf_token", "").encode("utf-8"), token.encode("utf-8")
    ):
        errors = ["This form has expired. Reload the page before saving."]
        status = 400
    else:
        try:
            existing = food_entries.find_one({"_id": entry_id})
            if existing is None:
                abort(404)
            values = request.form if request.method == "POST" else existing
            if request.method == "POST":
                entry, errors = validate_food_entry(request.form)
                if errors:
                    status = 400
                else:
                    result = food_entries.update_one({"_id": entry_id}, {"$set": entry})
                    if not result.matched_count:
                        abort(404)
                    flash("Changes saved successfully.", "edit:" + meal_id)
                    return redirect(url_for("edit_meal", meal_id=meal_id), code=303)
        except PyMongoError:
            errors = ["We couldn't confirm the database operation. Reload to check the saved entry before trying again."]
            status = 503
    notices = get_flashed_messages(category_filter=["edit:" + meal_id])
    return frontend.screen("edit_food_entry.html", "Edit food entry", preview=False,
                           values=values, errors=errors, notices=notices,
                           meal_choices=MEAL_CHOICES, csrf_token=token,
                           meal_id=meal_id), status


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
