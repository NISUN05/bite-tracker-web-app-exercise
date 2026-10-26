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

MEAL_CATEGORIES = ["Breakfast", "Lunch", "Dinner", "Snacks"]

@app.route("/db-test")
def db_test():
    client.admin.command("ping")
    return "Successfully connected to MongoDB!"

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/dashboard")
def dashboard2():
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

        return render_template(
            "today.html",
            grouped_entries=grouped_entries,
            summary=summary,
            today=today
        )

@app.route("/add", methods=["GET", "POST"])
def add_entry():
    if request.method == "POST":
        date_input = request.form.get("date")
        
        if date_input:
            date = datetime.strptime(date_input, "%Y-%m-%d")
        else:
            date = datetime.now()

        food_item = {
            "date": date,
            "item_name": request.form.get("item_name"),
            "meal_category": request.form.get("meal_category"),
            "calories": float(request.form.get("calories", 0)),
            "protein": float(request.form.get("protein", 0)),
            "carbs": float(request.form.get("carbs", 0)),
            "fat": float(request.form.get("fat", 0))
        }

        food_entries.insert_one(food_item)
        return redirect(url_for("today"))

    return render_template("add_entry.html", categories=MEAL_CATEGORIES)

@app.route("/edit/<entry_id>", methods=["GET", "POST"])
def edit_entry(entry_id):
    entry = food_entries.find_one({"_id": ObjectId(entry_id)})

    if request.method == "POST":
        date_input = request.form.get("date")
        
        if date_input:
            date = datetime.strptime(date_input, "%Y-%m-%d")
        else:
            date = datetime.now()

        updated_values = {
            "$set": {
                "date": date,
                "item_name": request.form.get("item_name"),
                "meal_category": request.form.get("meal_category"),
                "calories": float(request.form.get("calories", 0)),
                "protein": float(request.form.get("protein", 0)),
                "carbs": float(request.form.get("carbs", 0)),
                "fat": float(request.form.get("fat", 0))
            }
        }
        
        food_entries.update_one({"_id": ObjectId(entry_id)}, updated_values)
        return redirect("/today")

    return render_template("edit_meal.html", entry=entry, categories=MEAL_CATEGORIES)

@app.route("/delete/<entry_id>", methods=["GET", "POST"])
def delete_entry(entry_id):
    entry = food_entries.find_one({"_id": ObjectId(entry_id)})

    if request.method == "POST":
        food_entries.delete_one({"_id": ObjectId(entry_id)})
        return redirect("/today")

    return render_template("delete_meal.html", entry=entry)

@app.route("/weekly-summary")
def weekly_summary():
    today = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_start = today - timedelta(days=today.weekday())
    next_week = week_start + timedelta(days=7)

    # Include every day, even if no meals were logged.
    daily_totals = {
        (week_start + timedelta(days=i)).date(): {
            "calories": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
        }
        for i in range(7)
    }

    entries = food_entries.find({
        "date": {"$gte": week_start, "$lt": next_week}
    })

    for entry in entries:
        day = entry["date"].date()
        for nutrient in daily_totals[day]:
            daily_totals[day][nutrient] += float(
                entry.get(nutrient, 0) or 0
            )

    weekly_totals = {
        nutrient: sum(day[nutrient] for day in daily_totals.values())
        for nutrient in ("calories", "protein", "carbs", "fat")
    }

    daily_summary = [
        {"date": day, **totals}
        for day, totals in daily_totals.items()
    ]

    return render_template(
        "weekly_summary.html",
        week_start=week_start,
        week_end=next_week - timedelta(days=1),
        daily_summary=daily_summary,
        weekly_totals=weekly_totals,
    )

@app.route("/weekly-goal", methods=["GET", "POST"])
def weekly_goal():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    date = request.args.get("week", today.strftime("%Y-%m-%d"))
    date = datetime.strptime(date, "%Y-%m-%d")
    week_start = date - timedelta(days=date.weekday())
    next_week = week_start + timedelta(days=7)
    week_end = next_week - timedelta(days=1)
    week_key = week_start.strftime("%Y-%m-%d")

    return render_template(
        "weekly_goal.html",
        week_start=week_start,
        week_end=week_end,
        week_key=week_key,
        is_future_week=week_start > today
    )
  
@app.route("/history")
def history():
    all_entries = list(food_entries.find({"date": {"$exists": True}}).sort("date", DESCENDING))
    return render_template("history.html", entries=all_entries)

@app.route("/search", methods=["GET"])
def search():
    search_text = request.args.get("query", "").strip()
    date_text = request.args.get("date_filter", "").strip()
    category_text = request.args.get("category_filter", "").strip()

    filter_conditions = {"date": {"$exists": True}}

    if search_text != "":
        filter_conditions["item_name"] = {"$regex": search_text, "$options": "i"}

    if date_text != "":
        target_date = datetime.strptime(date_text, "%Y-%m-%d")
        next_day = target_date + timedelta(days=1)
        filter_conditions["date"] = {"$gte": target_date, "$lt": next_day}

    if category_text != "":
        filter_conditions["meal_category"] = category_text

    search_results = list(food_entries.find(filter_conditions).sort("date", DESCENDING))

    return render_template("search.html", results=search_results, categories=MEAL_CATEGORIES)

if __name__ == "__main__":
    app.run(debug=True)
