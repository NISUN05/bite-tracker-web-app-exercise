# Web Application Exercise

A little exercise to build a web application following an agile development process. See the [instructions](instructions.md) for more detail.

## Product vision statement

Bite Tracker helps users record, review, and organize their daily food intake by allowing them to log meals, track macronutrients, and search their food history in one convenient place.

## User stories

[User Stories Link](https://github.com/NISUN05/bite-tracker-web-app-exercise/issues?q=is%3Aissue+state%3Aclosed)

## Steps necessary to run the software

1. Setting up the repository and MongoDB connection
```bash
git clone https://github.com/NISUN05/bite-tracker-web-app-exercise.git
cd bite-tracker-web-app-exercise

python3 -m venv .venv          # Windows: python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp env.example .env            # Windows: copy env.example .env
```

Then open `.env` and fill in your MongoDB details:

```
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGO_DBNAME=bite_tracker
```

If you were given a `.env` file, just put it in the project folder instead.

2. Running the app

```bash
python3 app.py
```

Go to <http://127.0.0.1:5000/db-test> to check the database is connected. It should say "Successfully connected to MongoDB!"

Then open the app at <http://127.0.0.1:5000/>.

Press `Ctrl + C` to stop the app.


## Task boards

[Bite Tracker - Sprint 1](https://github.com/users/NISUN05/projects/10/views/2)

[Bite Tracker - Sprint 2](https://github.com/users/NISUN05/projects/11/views/2)
