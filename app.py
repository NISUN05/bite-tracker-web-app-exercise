import certifi
import os

from dotenv import load_dotenv
from flask import Flask
from pymongo import MongoClient

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


@app.route("/")
def home():
    return "Bite Tracker is running!"


@app.route("/db-test")
def db_test():
    client.admin.command("ping")
    return "Successfully connected to MongoDB!"


if __name__ == "__main__":
    app.run(debug=True)
