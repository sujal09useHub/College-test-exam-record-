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
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    role = session.get("role")

    if role == "student":
        return redirect("/student")

    if role == "teacher":
        return redirect("/teacher")

    if role == "developer":
        return redirect("/admin")

    return "Invalid role", 403
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "developer":
        return "Access Denied", 403

 return """
    <h1>👨‍💻 Developer Dashboard</h1>

    <p>Welcome, Developer!</p>

    <hr>

    <h2>👥 User Management</h2>

    <form method="POST" action="/admin/add-user">
        <input name="name" placeholder="Name" required><br><br>
        <input name="email" type="email" placeholder="Email" required><br><br>
        <input name="password" type="password"
               placeholder="Password" required><br><br>

        <select name="role" required>
            <option value="student">🎓 Student</option>
            <option value="teacher">👨‍🏫 Teacher</option>
        </select>

        <br><br>
        <button type="submit">➕ Add User</button>
    </form>

    <hr>

    <a href="/logout">Logout</a>
    """
@app.route("/teacher")
def teacher():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "teacher":
        return "Access Denied", 403

    return """
    <h1>👨‍🏫 Teacher Dashboard</h1>

    <p>Welcome, Teacher!</p>

    <hr>

    <h2>👨‍🎓 Students</h2>
    <p>Student management will be added next.</p>

    <h2>📊 Test Marks</h2>
    <p>Add / Edit / Delete marks will be added next.</p>

    <br>
    <a href="/logout">Logout</a>
    """
@app.route("/student")
def student():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "student":
        return "Access Denied", 403

    r = requests.get(
        SUPABASE_URL + "/rest/v1/test_records",
        headers=db_headers(),
        params={
            "student_id": "eq." + str(session["user_id"]),
            "select": "id,subject_id,test_name,marks,total_marks,test_date",
            "order": "test_date.desc"
        },
        timeout=10
    )

    if r.status_code != 200:
        return "Database Error", 500

    records = r.json()

    rows = ""

    for x in records:
        rows += f"""
        <tr>
            <td>{x["test_name"]}</td>
            <td>{x["marks"]}/{x["total_marks"]}</td>
            <td>{x["test_date"] or ""}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="3">No test records yet.</td>
        </tr>
        """

    return f"""
    <h1>🎓 Student Dashboard</h1>

    <p>Welcome, {session["name"]}</p>

    <table border="1" cellpadding="10">
        <tr>
            <th>Test</th>
            <th>Marks</th>
            <th>Date</th>
        </tr>
        {rows}
    </table>

    <br>
    <a href="/logout">Logout</a>
    """
@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>College Test Record</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: Arial;
                background: #f2f5f9;
                padding: 20px;
            }

            .box {
                max-width: 400px;
                margin: 50px auto;
                background: white;
                padding: 25px;
                border-radius: 15px;
            }

            input, button {
                width: 100%;
                padding: 12px;
                margin-top: 10px;
                box-sizing: border-box;
            }

            button {
                background: #2563eb;
                color: white;
                border: 0;
                border-radius: 8px;
            }
        </style>
    </head>

    <body>
        <div class="box">
            <h1>🎓 College Test Record</h1>
            <p>Login to continue</p>

            <form method="POST" action="/login">
                <input type="email" name="email"
                       placeholder="Email" required>

                <input type="password" name="password"
                       placeholder="Password" required>

                <button type="submit">🔐 Login</button>
            </form>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)