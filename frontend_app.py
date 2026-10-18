"""Flask routes for a frontend-only Macros handoff.

Every data value below is sample data. The backend teammate should replace
sample_meals() with MongoDB reads and add POST handlers for the HTML forms.
"""
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, render_template, request

load_dotenv(Path(__file__).with_name(".env"))
app = Flask(__name__)
GOALS = {"calories": 2000, "protein": 150, "carbs": 250, "fat": 70, "water": 2000}


def sample_meals():
    """Presentation fixtures only; this function does not query a database."""
    today = datetime.now().astimezone().replace(second=0, microsecond=0)
    items = [
        ("oatmeal-berries", "Oatmeal and berries", 350, 12, 58, 8, today.replace(hour=8, minute=0)),
        ("chicken-bowl", "Chicken rice bowl", 620, 42, 70, 18, today.replace(hour=12, minute=30)),
        ("apple-snack", "Apple snack", 95, 0, 25, 0, (today - timedelta(days=1)).replace(hour=15, minute=0)),
    ]
    return [
        {"id": mid, "name": name, "calories": calories, "protein": protein,
         "carbs": carbs, "fat": fat, "loggedAt": logged.isoformat(),
         "input_date": logged.strftime("%Y-%m-%dT%H:%M"),
         "date_label": logged.strftime("%b %d, %I:%M %p")}
        for mid, name, calories, protein, carbs, fat, logged in items
    ]


def sample_meal(meal_id):
    meal = next((meal for meal in sample_meals() if meal["id"] == meal_id), None)
    if meal is None:
        abort(404)
    return meal


def screen(template, title, active="", subtitle="", **context):
    values = {"title": title, "active": active, "subtitle": subtitle,
              "preview": True, "goals": GOALS, "display_name": "Friend"}
    values.update(context)
    return render_template(template, **values)


@app.get("/")
def index():
    today = datetime.now().astimezone()
    meals = [meal for meal in sample_meals() if datetime.fromisoformat(meal["loggedAt"]).date() == today.date()]
    totals = {key: sum(meal[key] for meal in meals) for key in ("calories", "protein", "carbs", "fat")}
    ratio = lambda key: min(1, max(0, totals[key] / GOALS[key])) if GOALS[key] else 0
    rings = []
    for key, radius, color, label, legend_color in [
        ("calories", 54, "url(#calorie-gradient)", "Calories", "#ff5b58"),
        ("protein", 42, "#5dd675", "Protein", "#5dd675"),
        ("carbs", 30, "#4f8cff", "Carbs", "#4f8cff"),
    ]:
        circumference = 2 * math.pi * radius
        rings.append({"radius": radius, "color": color, "label": label,
                      "legend_color": legend_color, "circumference": circumference,
                      "offset": circumference * (1 - ratio(key)),
                      "remaining": max(0, GOALS[key] - totals[key]),
                      "unit": "" if key == "calories" else "g"})
    macros = [{"label": key.title(), "color": color, "value": totals[key],
               "remaining": max(0, GOALS[key] - totals[key]), "percent": round(ratio(key) * 100)}
              for key, color in [("protein", "#5dd675"), ("carbs", "#5b91ff"), ("fat", "#ffd35b")]]
    summary = {**totals, "remaining": max(0, GOALS["calories"] - totals["calories"]),
               "percent": round(ratio("calories") * 100)}
    return screen("dashboard.html", "Today", "today", today.strftime("%A, %B %d"),
                  meals=meals, summary=summary, rings=rings, macros=macros)


@app.get("/meals")
def meals():
    return screen("meals.html", "Meal history", "meals", "Your nutrition timeline", meals=sample_meals())


@app.get("/meals/new")
def add_meal():
    return screen("add_meal.html", "Add meal", subtitle="Enter a food and its calories", meal=None,
                  default_date=datetime.now().strftime("%Y-%m-%dT%H:%M"))


@app.get("/meals/<meal_id>/edit")
def edit_meal(meal_id):
    return screen("edit_meal.html", "Edit meal", "meals", "Update your food entry", meal=sample_meal(meal_id))


@app.get("/meals/<meal_id>/delete")
def delete_meal(meal_id):
    return screen("delete_meal.html", "Delete meal", "meals", "Review before removing", meal=sample_meal(meal_id))


@app.get("/search")
def search():
    query = request.args.get("q", "").strip()[:120]
    matches = [meal for meal in sample_meals() if query.casefold() in meal["name"].casefold()] if query else []
    return screen("search.html", "Search meals", "search", "Find entries by food name", query=query,
                  meals=matches, empty_message="Try a different food name.")


@app.get("/goals")
def goals():
    return screen("goals.html", "Profile & Goals", subtitle="Your daily targets")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("FLASK_PORT", "5001")))
