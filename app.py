import os
import certifi
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient, DESCENDING

load_dotenv()

app = Flask(__name__)

mongo_uri = os.getenv("MONGO_URI")
database_name = os.getenv("MONGO_DBNAME")

client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
db = client[database_name]
food_entries = db["food_entries"]

MEAL_CHOICES = ["Breakfast", "Lunch", "Dinner", "Snacks"]

@app.route("/db-test")
def db_test():
    client.admin.command("ping")
    return "Successfully connected to MongoDB!"

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/today")
def today():
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
    
        query = {"date": {"$gte": today, "$lt": tomorrow}}
        entries_today = list(food_entries.find(query))
    
        grouped_entries = {
            "Breakfast": [],
            "Lunch": [],
            "Dinner": [],
            "Snacks": []
        }
        
        total_calories = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0
    
        for entry in entries_today:
            category = entry.get("meal_category")
            if category in grouped_entries:
                grouped_entries[category].append(entry)
    
            total_calories += float(entry.get("calories", 0))
            total_protein += float(entry.get("protein", 0))
            total_carbs += float(entry.get("carbs", 0))
            total_fat += float(entry.get("fat", 0))
    
        summary = {
            "calories": total_calories,
            "protein": total_protein,
            "carbs": total_carbs,
            "fat": total_fat
        }

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
