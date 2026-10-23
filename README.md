# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

Bite Tracker helps users record, review, and organize their daily food intake by allowing them to log meals, track macronutrients, and search their food history in one convenient place.

## User stories

[Link](https://github.com/NISUN05/bite-tracker-web-app-exercise/issues)

## Steps necessary to run the software

1. Clone the shared team repository and enter it:

   ```bash
   git clone https://github.com/NISUN05/bite-tracker-web-app-exercise.git
   cd bite-tracker-web-app-exercise
   ```

2. Use Python 3.9 or newer and create a virtual environment:

   ```bash
   python3 --version
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Jessie's Mac, `python3` points to Python 3.6; use `/usr/bin/python3`
   (Python 3.9) for the version check and environment creation instead.
   On Windows, use `python -m venv .venv` and activate with
   `.venv\Scripts\Activate.ps1` in PowerShell.

3. Run the required course setup in every new clone, resolve reported issues,
   and approve the project hooks in each installed AI coding tool as instructed:

   ```bash
   python .automations/setup.py
   ```

4. Install application dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

5. Copy `env.example` to `.env` (`cp env.example .env` on Mac/Linux or
   `Copy-Item env.example .env` in PowerShell). Fill in `MONGO_URI` and
   `MONGO_DBNAME` with the team's development settings. Keep `.env` private;
   it is excluded from Git. In Atlas, the database user must have access to the
   development database and your current IP must be allowed by Network Access.

6. Start the local application:

   ```bash
   python app.py
   ```

   Open <http://127.0.0.1:5000/> for the team's UI and use its Add button,
   or open <http://127.0.0.1:5000/meals/new> directly. The older `/add` URL
   works too. Add and Edit entries are saved to MongoDB. Use **View and edit saved entries**
   on the Add page (or `/entries`) to select a real record. The other screens currently
   retain their labeled sample-data previews until their backend features
   are connected. New records will not yet appear in those sample lists.
   <http://127.0.0.1:5000/db-test> checks the database connection.

   For the original frontend-only preview, run `python frontend_app.py`
   and open <http://127.0.0.1:5001/>. That separate preview does not save data;
   use `python app.py` on port 5000 to test the real Add feature.

7. Install test dependencies and run the Add and Edit automated tests from the repository root:

   ```bash
   python -m pip install -r requirements-dev.txt
   python -m unittest discover -s tests -v
   ```

   These tests replace MongoDB with a test double and never write to Atlas.
   See [Add food entry integration notes](docs/add-food-entry.md) for the
   proposed document fields, manual checks, and homepage integration.
   See [Edit integration notes](docs/edit-food-entry.md) for real-record URLs and limitations.

## Task boards

[Bite Tracker - Sprint 1](https://github.com/users/NISUN05/projects/10/views/2)

[Bite Tracker - Sprint 2](https://github.com/users/NISUN05/projects/11/views/2)
