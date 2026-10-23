"""Run with: python -m unittest discover -s tests -v (no database needed)."""

import os
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from markupsafe import escape
from pymongo.errors import ServerSelectionTimeoutError

# Import the application without opening a real MongoDB connection or using secrets.
with patch.dict(os.environ, {
    "MONGO_URI": "mongodb://localhost:27017/",
    "MONGO_DBNAME": "bite_tracker_test",
}):
    with patch("pymongo.MongoClient"):
        import app as food_app


class AddFoodEntryTests(unittest.TestCase):
    def setUp(self):
        food_app.app.config["TESTING"] = True
        self.browser = food_app.app.test_client()
        self.collection = MagicMock(spec=["insert_one"])
        collection_patch = patch.object(food_app, "food_entries", self.collection)
        collection_patch.start()
        self.addCleanup(collection_patch.stop)
        self.valid = {
            "date": "2026-10-18",
            "food_name": "  Test oatmeal  ",
            "meal": "breakfast",
            "calories": "150",
            "protein": "5.5",
            "carbs": "27",
            "fat": "0",
        }

    def test_get_shows_form_without_writing(self):
        response = self.browser.get("/add")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Save entry", html)
        self.assertIn('data-preview="false"', html)
        self.assertIn('value="{}"'.format(date.today().isoformat()), html)
        self.assertIn('<option value="">Choose a meal</option>', html)
        self.assertNotIn("saved successfully", html)
        for field in self.valid:
            self.assertIn('name="{}"'.format(field), html)
        with self.browser.get("/static/add_food_entry.css") as stylesheet:
            self.assertEqual(stylesheet.status_code, 200)
        self.collection.insert_one.assert_not_called()

    def test_valid_entry_is_trimmed_and_saved_as_numbers(self):
        response = self.browser.post("/add", data=self.valid)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/meals/new?saved=1")
        self.collection.insert_one.assert_called_once_with({
            "date": "2026-10-18",
            "food_name": "Test oatmeal",
            "meal": "breakfast",
            "calories": 150.0,
            "protein": 5.5,
            "carbs": 27.0,
            "fat": 0.0,
        })
        document = self.collection.insert_one.call_args.args[0]
        for field in ("calories", "protein", "carbs", "fat"):
            self.assertIsInstance(document[field], float)

    def test_success_redirect_and_refresh_do_not_insert_again(self):
        response = self.browser.post("/add", data=self.valid)
        for _ in range(2):
            saved_page = self.browser.get(response.headers["Location"])
            self.assertEqual(saved_page.status_code, 200)
            self.assertIn("Food entry saved successfully.", saved_page.get_data(as_text=True))
            self.assertNotIn('value="  Test oatmeal  "', saved_page.get_data(as_text=True))
        self.collection.insert_one.assert_called_once()

    def test_all_meals_and_valid_calendar_dates_are_accepted(self):
        for meal in ("breakfast", "lunch", "dinner", "snacks"):
            for valid_date in ("2024-02-29", "2030-01-01"):
                with self.subTest(meal=meal, date=valid_date):
                    self.collection.reset_mock()
                    payload = dict(self.valid, meal=meal, date=valid_date, food_name="燕麦")
                    self.assertEqual(self.browser.post("/add", data=payload).status_code, 303)
                    self.collection.insert_one.assert_called_once()

    def test_each_required_field_is_checked_on_the_server(self):
        for field in self.valid:
            with self.subTest(field=field):
                payload = dict(self.valid)
                payload.pop(field)
                response = self.browser.post("/add", data=payload)
                self.assertEqual(response.status_code, 400)
                self.collection.insert_one.assert_not_called()

    def test_whitespace_only_food_names_are_rejected(self):
        for name in ("", "   ", "\t\n"):
            with self.subTest(name=name):
                response = self.browser.post("/add", data=dict(self.valid, food_name=name))
                self.assertEqual(response.status_code, 400)
                self.assertIn("Please enter a food name.", response.get_data(as_text=True))
                self.collection.insert_one.assert_not_called()

    def test_invalid_dates_are_rejected(self):
        for invalid_date in (
            "", "2026-02-30", "2026-13-01", "2025-02-29", "20261018",
            "2026-1-1", "2026-10-18T00:00:00", "not-a-date",
        ):
            with self.subTest(date=invalid_date):
                response = self.browser.post("/add", data=dict(self.valid, date=invalid_date))
                self.assertEqual(response.status_code, 400)
                self.collection.insert_one.assert_not_called()

    def test_invalid_meals_are_rejected(self):
        for meal in ("", "snack", "Breakfast", "brunch"):
            with self.subTest(meal=meal):
                response = self.browser.post("/add", data=dict(self.valid, meal=meal))
                self.assertEqual(response.status_code, 400)
                self.collection.insert_one.assert_not_called()

    def test_invalid_nutrients_never_reach_the_database(self):
        for field in ("calories", "protein", "carbs", "fat"):
            for value in ("", " ", "abc", "-1", "-0.1", "NaN", "inf", "-inf", "Infinity", "1e309"):
                with self.subTest(field=field, value=value):
                    payload = dict(self.valid)
                    payload[field] = value
                    response = self.browser.post("/add", data=payload)
                    self.assertEqual(response.status_code, 400)
                    self.collection.insert_one.assert_not_called()

    def test_error_retains_inputs_and_escapes_html(self):
        unsafe_name = 'Oats "><script>alert(1)</script>'
        payload = dict(self.valid, food_name=unsafe_name, meal="dinner", calories="-1")
        response = self.browser.post("/add", data=payload)
        self.assertEqual(response.status_code, 400)
        html = response.get_data(as_text=True)
        self.assertIn(str(escape(unsafe_name)), html)
        self.assertNotIn("<script>", html)
        self.assertIn('value="2026-10-18"', html)
        self.assertIn('value="5.5"', html)
        self.assertIn('value="27"', html)
        self.assertIn('value="0"', html)
        self.assertRegex(html, r'value="dinner"\s+selected')
        self.collection.insert_one.assert_not_called()

    def test_database_failure_keeps_form_without_success_or_private_error(self):
        self.collection.insert_one.side_effect = ServerSelectionTimeoutError("private connection detail")
        with self.assertLogs(food_app.app.logger, level="WARNING") as logs:
            response = self.browser.post("/add?saved=1", data=self.valid)
        self.assertEqual(response.status_code, 503)
        html = response.get_data(as_text=True)
        self.assertIn("couldn&#39;t confirm", html)
        self.assertIn('value="  Test oatmeal  "', html)
        self.assertIn('value="150"', html)
        self.assertNotIn("saved successfully", html)
        self.assertNotIn("private connection detail", html)
        self.assertNotIn("private connection detail", " ".join(logs.output))

    def test_unexpected_fields_are_not_saved(self):
        payload = dict(self.valid, _id="client-selected-id", owner="admin", extra="ignore me")
        self.assertEqual(self.browser.post("/add", data=payload).status_code, 303)
        document = self.collection.insert_one.call_args.args[0]
        self.assertEqual(set(document), set(self.valid))

    def test_team_ui_add_route_saves_through_the_same_handler(self):
        page = self.browser.get("/meals/new")
        self.assertEqual(page.status_code, 200)
        self.assertIn('action="/meals/new"', page.get_data(as_text=True))
        response = self.browser.post("/meals/new", data=self.valid)
        self.assertEqual(response.status_code, 303)
        self.collection.insert_one.assert_called_once()

    def test_existing_ui_routes_render_without_database_writes(self):
        for path in (
            "/", "/meals", "/search", "/goals",
            "/meals/oatmeal-berries/edit", "/meals/oatmeal-berries/delete",
        ):
            with self.subTest(path=path):
                page = self.browser.get(path)
                self.assertEqual(page.status_code, 200)
                self.assertIn('data-preview="true"', page.get_data(as_text=True))
                self.assertIn("Changes won't be saved.", page.get_data(as_text=True))
        self.assertIn('href="/meals/new"', self.browser.get("/").get_data(as_text=True))
        self.collection.insert_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
