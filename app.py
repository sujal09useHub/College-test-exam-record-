from flask import Flask, request, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "change-this-later"
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")


def db_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": "Bearer " + SUPABASE_KEY,
        "Content-Type": "application/json"
    }
def create_user(name, email, password, role):
    data = {
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "role": role
    }

    return requests.post(
        SUPABASE_URL + "/rest/v1/users",
        headers=db_headers(),
        json=data,
        timeout=10
    )
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    r = requests.get(
        SUPABASE_URL + "/rest/v1/users",
        headers=db_headers(),
        params={
            "email": "eq." + email,
            "select": "id,name,email,password_hash,role",
            "limit": 1
        },
        timeout=10
    )

    if r.status_code != 200:
        return "Database Error", 500

    users = r.json()

    if not users:
        return "Invalid email or password", 401

    user = users[0]

    if not check_password_hash(user["password_hash"], password):
        return "Invalid email or password", 401

    session["user_id"] = user["id"]
    session["name"] = user["name"]
    session["email"] = user["email"]
    session["role"] = user["role"]

    return redirect("/dashboard")
@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>College Test Record</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body>
        <h1>🎓 College Test Record</h1>
        <p>Website setup successful!</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)