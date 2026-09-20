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
SUPABASE_KEY = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get("SUPABASE_KEY", "")


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
@app.route("/setup-developer")
def setup_developer():
    password_hash = generate_password_hash("admin123")

    r = requests.patch(
        SUPABASE_URL + "/rest/v1/users",
        headers=db_headers(),
        params={"email": "eq.admin@gmail.com"},
        json={
            "name": "Developer",
            "password_hash": password_hash,
            "role": "developer"
        },
        timeout=10
    )

    return r.text, r.status_code
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

    r = requests.get(
        SUPABASE_URL + "/rest/v1/users",
        headers=db_headers(),
        params={
            "select": "id,name,email,role",
            "order": "name.asc"
        },
        timeout=10
    )

    if r.status_code != 200:
        return "Database Error: " + r.text, 500

    users = r.json()
    
        # Get subjects
    subjects_response = requests.get(
        SUPABASE_URL + "/rest/v1/subjects",
        headers=db_headers(),
        params={
            "select": "id,name",
            "order": "name.asc"
        },
        timeout=10
    )

    if subjects_response.status_code != 200:
        return "Database Error: " + subjects_response.text, 500

    subjects = subjects_response.json()

    subject_rows = ""

    for subject in subjects:
        subject_rows += f"""
        <tr>
            <td>{subject["name"]}</td>

            <td>
                <a href="/admin/edit-subject/{subject["id"]}">
                    ✏️ Edit
                </a>

                <form method="POST"
                      action="/admin/delete-subject/{subject["id"]}"
                      style="display:inline;"
                      onsubmit="return confirm('Delete this subject?');">

                    <button type="submit"
                            style="background:#dc2626;color:white;border:0;padding:7px 10px;border-radius:6px;">
                        🗑️ Delete
                    </button>

                </form>
            </td>
        </tr>
        """

    if not subject_rows:
        subject_rows = """
        <tr>
            <td colspan="2">No subjects found.</td>
        </tr>
        """

    rows = ""

    for user in users:
        rows += f"""
        <tr>
            <td>{user["name"]}</td>
            <td>{user["email"]}</td>
            <td>{user["role"]}</td>
            <td>
                <form method="POST"
                      action="/admin/delete-user"
                      onsubmit="return confirm('Delete this user?');">
                    <input type="hidden"
                           name="user_id"
                           value="{user["id"]}">
                    <button type="submit">🗑️ Delete</button>
                </form>
            </td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="4">No users found.</td>
        </tr>
        """

    return f"""
    <h1>👨‍💻 Developer Dashboard</h1>

    <p>Welcome, {session["name"]}</p>

    <hr>

    <h2>➕ Add Student / Teacher</h2>

    <form method="POST" action="/admin/add-user">
        <input name="name" placeholder="Name" required><br><br>

        <input name="email"
               type="email"
               placeholder="Email"
               required><br><br>

        <input name="password"
               type="password"
               placeholder="Password"
               required><br><br>

        <select name="role" required>
            <option value="student">🎓 Student</option>
            <option value="teacher">👨‍🏫 Teacher</option>
        </select>

        <br><br>

        <button type="submit">➕ Add User</button>
    </form>

    <hr>

    <h2>👥 Users</h2>

    <table border="1" cellpadding="10">
        <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Action</th>
        </tr>

        {rows}
    </table>
    <hr>

<h2>📚 Manage Subjects</h2>

<form method="POST" action="/admin/add-subject">

    <input
        type="text"
        name="name"
        placeholder="Enter Subject Name"
        required
    >

    <button type="submit">
        ➕ Add Subject
    </button>

</form>

<br>

<table border="1" cellpadding="10">

    <tr>
        <th>Subject</th>
        <th>Action</th>
    </tr>

    {subject_rows}

</table>
    <br>

    <a href="/logout">Logout</a>
    """
@app.route("/admin/add-user", methods=["POST"])
def admin_add_user():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "developer":
        return "Access Denied", 403

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "")

    if not name or not email or not password:
        return "All fields are required", 400

    if role not in ["student", "teacher"]:
        return "Invalid role", 400

    r = create_user(name, email, password, role)

    if r.status_code not in [200, 201]:
        return "Could not create user: " + r.text, 400

    return """
    <h2>✅ User created successfully!</h2>
    <a href="/admin">← Back to Admin Dashboard</a>
    """
@app.route("/admin/add-subject", methods=["POST"])
def admin_add_subject():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "developer":
        return "Access Denied", 403

    name = request.form.get("name", "").strip()

    if not name:
        return "Subject name is required", 400

    # Check duplicate subject
    check = requests.get(
        SUPABASE_URL + "/rest/v1/subjects",
        headers=db_headers(),
        params={
            "name": "eq." + name,
            "select": "id",
            "limit": 1
        },
        timeout=10
    )

    if check.status_code != 200:
        return "Database Error: " + check.text, 500

    if check.json():
        return """
        <h2>⚠️ Subject already exists!</h2>
        <a href="/admin">← Back to Admin</a>
        """

    data = {
        "name": name
    }

    r = requests.post(
        SUPABASE_URL + "/rest/v1/subjects",
        headers=db_headers(),
        json=data,
        timeout=10
    )

    if r.status_code not in [200, 201]:
        return "Could not add subject: " + r.text, 400

    return redirect("/admin")
@app.route("/admin/edit-subject/<int:subject_id>", methods=["GET", "POST"])
def admin_edit_subject(subject_id):

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "developer":
        return "Access Denied", 403

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        if not name:
            return "Subject name is required", 400

        data = {
            "name": name
        }

        r = requests.patch(
            SUPABASE_URL + "/rest/v1/subjects",
            headers=db_headers(),
            params={
                "id": "eq." + str(subject_id)
            },
            json=data,
            timeout=10
        )

        if r.status_code not in [200, 204]:
            return "Could not update subject: " + r.text, 400

        return redirect("/admin")

    # Get subject
    r = requests.get(
        SUPABASE_URL + "/rest/v1/subjects",
        headers=db_headers(),
        params={
            "id": "eq." + str(subject_id),
            "select": "id,name",
            "limit": 1
        },
        timeout=10
    )

    if r.status_code != 200:
        return "Database Error: " + r.text, 500

    subjects = r.json()

    if not subjects:
        return "Subject not found", 404

    subject = subjects[0]

    return f"""
    <!DOCTYPE html>
    <html>

    <head>

        <title>Edit Subject</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <style>

            body {{
                font-family: Arial;
                background: #f2f5f9;
                padding: 20px;
            }}

            .box {{
                max-width: 450px;
                margin: 50px auto;
                background: white;
                padding: 25px;
                border-radius: 15px;
            }}

            input, button {{
                width: 100%;
                padding: 12px;
                margin-top: 10px;
                box-sizing: border-box;
            }}

            button {{
                background: #2563eb;
                color: white;
                border: 0;
                border-radius: 8px;
            }}

        </style>

    </head>

    <body>

    <div class="box">

        <h1>✏️ Edit Subject</h1>

        <form method="POST">

            <label>📚 Subject Name</label>

            <input
                type="text"
                name="name"
                value="{subject["name"]}"
                required
            >

            <button type="submit">
                💾 Save Changes
            </button>

        </form>

        <br>

        <a href="/admin">
            ← Back to Admin Dashboard
        </a>

    </div>

    </body>

    </html>
    """
@app.route("/admin/delete-subject/<int:subject_id>", methods=["POST"])
def admin_delete_subject(subject_id):

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "developer":
        return "Access Denied", 403

    r = requests.delete(
        SUPABASE_URL + "/rest/v1/subjects",
        headers=db_headers(),
        params={
            "id": "eq." + str(subject_id)
        },
        timeout=10
    )

    if r.status_code not in [200, 204]:
        return "Could not delete subject: " + r.text, 400

    return redirect("/admin")

@app.route("/admin/delete-user", methods=["POST"])
def admin_delete_user():

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "developer":
        return "Access Denied", 403

    user_id = request.form.get("user_id", "")

    if not user_id:
        return "User ID required", 400

    # Developer स्वतःला delete करू शकणार नाही
    if str(user_id) == str(session["user_id"]):
        return "You cannot delete yourself", 400

    r = requests.delete(
        SUPABASE_URL + "/rest/v1/users",
        headers=db_headers(),
        params={
            "id": "eq." + str(user_id)
        },
        timeout=10
    )

    if r.status_code not in [200, 204]:
        return "Could not delete user: " + r.text, 400

    return redirect("/admin")

@app.route("/teacher")
def teacher():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "teacher":
        return "Access Denied", 403

    # Get students
    students_response = requests.get(
        SUPABASE_URL + "/rest/v1/users",
        headers=db_headers(),
        params={
            "role": "eq.student",
            "select": "id,name,email",
            "order": "name.asc"
        },
        timeout=10
    )

    if students_response.status_code != 200:
        return "Database Error: " + students_response.text, 500

    students = students_response.json()

    # Get subjects
    subjects_response = requests.get(
        SUPABASE_URL + "/rest/v1/subjects",
        headers=db_headers(),
        params={
            "select": "id,name",
            "order": "name.asc"
        },
        timeout=10
    )

    if subjects_response.status_code != 200:
        return "Database Error: " + subjects_response.text, 500

    subjects = subjects_response.json()

    # Get all test records
    records_response = requests.get(
        SUPABASE_URL + "/rest/v1/test_records",
        headers=db_headers(),
        params={
            "select": "id,student_id,subject_id,test_name,marks,total_marks,test_date",
            "order": "test_date.desc"
        },
        timeout=10
    )

    if records_response.status_code != 200:
        return "Database Error: " + records_response.text, 500

    records = records_response.json()

    # Student dropdown
    student_options = ""

    for student in students:
        student_options += f"""
        <option value="{student["id"]}">
            {student["name"]} - {student["email"]}
        </option>
        """

    # Subject dropdown
    subject_options = ""

    for subject in subjects:
        subject_options += f"""
        <option value="{subject["id"]}">
            {subject["name"]}
        </option>
        """

    # Create lookup dictionaries
    student_names = {
        str(student["id"]): student["name"]
        for student in students
    }

    subject_names = {
        str(subject["id"]): subject["name"]
        for subject in subjects
    }

    # Records table
    rows = ""

    for record in records:
        student_name = student_names.get(
            str(record["student_id"]),
            "Unknown Student"
        )

        subject_name = subject_names.get(
            str(record["subject_id"]),
            "Unknown Subject"
        )

        rows += f"""
        <tr>
            <td>{student_name}</td>
            <td>{subject_name}</td>
            <td>{record["test_name"]}</td>
            <td>{record["marks"]}/{record["total_marks"]}</td>
            <td>{record["test_date"]}</td>

            <td>
                <a href="/teacher/edit-record/{record["id"]}">
                    ✏️ Edit
                </a>

                <form method="POST"
                      action="/teacher/delete-record/{record["id"]}"
                      style="display:inline;"
                      onsubmit="return confirm('Delete this test record?');">

                    <button type="submit">
                        🗑️ Delete
                    </button>

                </form>
            </td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="6">
                No test records yet.
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>

    <head>

        <title>Teacher Dashboard</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <style>

            body {{
                font-family: Arial;
                background: #f2f5f9;
                padding: 15px;
            }}

            .box {{
                max-width: 1100px;
                margin: auto;
                background: white;
                padding: 20px;
                border-radius: 15px;
            }}

            input, select, button {{
                width: 100%;
                padding: 12px;
                margin-top: 8px;
                margin-bottom: 12px;
                box-sizing: border-box;
            }}

            button {{
                background: #2563eb;
                color: white;
                border: 0;
                border-radius: 8px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}

            th, td {{
                border: 1px solid #ccc;
                padding: 10px;
                text-align: left;
            }}

            th {{
                background: #f1f5f9;
            }}

            .delete-btn {{
                background: #dc2626;
                width: auto;
                padding: 7px 10px;
                margin: 5px;
            }}

            .edit-link {{
                display: inline-block;
                background: #16a34a;
                color: white;
                padding: 7px 10px;
                border-radius: 6px;
                text-decoration: none;
            }}

        </style>

    </head>

    <body>

    <div class="box">

        <h1>👨‍🏫 Teacher Dashboard</h1>

        <p>
            Welcome, {session["name"]}
        </p>

        <hr>

        <h2>➕ Add Test Marks</h2>

        <form method="POST"
              action="/teacher/add-record">

            <label>🎓 Student</label>

            <select name="student_id" required>

                <option value="">
                    Select Student
                </option>

                {student_options}

            </select>

            <label>📚 Subject</label>

            <select name="subject_id" required>

                <option value="">
                    Select Subject
                </option>

                {subject_options}

            </select>

            <label>📝 Test Name</label>

            <input
                type="text"
                name="test_name"
                placeholder="Example: Unit Test 1"
                required
            >

            <label>📊 Marks</label>

            <input
                type="number"
                name="marks"
                min="0"
                step="1"
                required
            >

            <label>📋 Total Marks</label>

            <input
                type="number"
                name="total_marks"
                min="1"
                step="1"
                required
            >

            <label>📅 Test Date</label>

            <input
                type="date"
                name="test_date"
                required
            >

            <button type="submit">
                ➕ Add Test Record
            </button>

        </form>

        <hr>

        <h2>📊 All Student Test Records</h2>

        <table>

            <tr>
                <th>Student</th>
                <th>Subject</th>
                <th>Test</th>
                <th>Marks</th>
                <th>Date</th>
                <th>Action</th>
            </tr>

            {rows}

        </table>

        <br>

        <a href="/logout">
            🚪 Logout
        </a>

    </div>

    </body>

    </html>
    """

@app.route("/teacher/add-record", methods=["POST"])
def teacher_add_record():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "teacher":
        return "Access Denied", 403

    student_id = request.form.get("student_id", "")
    subject_id = request.form.get("subject_id", "")
    test_name = request.form.get("test_name", "").strip()
    marks = request.form.get("marks", "")
    total_marks = request.form.get("total_marks", "")
    test_date = request.form.get("test_date", "")

    if not all([
        student_id,
        subject_id,
        test_name,
        marks,
        total_marks,
        test_date
    ]):
        return "All fields are required", 400

    try:
        marks_value = int(marks)
        total_marks_value = int(total_marks)
    except ValueError:
        return "Marks must be whole numbers", 400

    if marks_value < 0:
        return "Marks cannot be negative", 400

    if total_marks_value <= 0:
        return "Total marks must be greater than 0", 400

    if marks_value > total_marks_value:
        return "Marks cannot be greater than total marks", 400

    data = {
        "student_id": student_id,
        "subject_id": subject_id,
        "test_name": test_name,
        "marks": marks_value,
        "total_marks": total_marks_value,
        "test_date": test_date
    }

    r = requests.post(
        SUPABASE_URL + "/rest/v1/test_records",
        headers=db_headers(),
        json=data,
        timeout=10
    )

    if r.status_code not in [200, 201]:
        return "Could not add test record: " + r.text, 400

    return """
    <h2>✅ Test record added successfully!</h2>

    <a href="/teacher">
        ← Back to Teacher Dashboard
    </a>
    """
@app.route("/teacher/edit-record/<int:record_id>", methods=["GET", "POST"])
def teacher_edit_record(record_id):

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "teacher":
        return "Access Denied", 403

    if request.method == "POST":

        test_name = request.form.get("test_name", "").strip()
        marks = request.form.get("marks", "")
        total_marks = request.form.get("total_marks", "")
        test_date = request.form.get("test_date", "")

        if not all([
            test_name,
            marks,
            total_marks,
            test_date
        ]):
            return "All fields are required", 400

        try:
           marks_value = int(marks)
           total_marks_value = int(total_marks)
        except ValueError:
           return "Marks must be whole numbers", 400

        if marks_value < 0:
            return "Marks cannot be negative", 400

        if total_marks_value <= 0:
            return "Total marks must be greater than 0", 400

        if marks_value > total_marks_value:
            return "Marks cannot be greater than total marks", 400

        data = {
            "test_name": test_name,
            "marks": marks_value,
            "total_marks": total_marks_value,
            "test_date": test_date
        }

        r = requests.patch(
            SUPABASE_URL + "/rest/v1/test_records",
            headers=db_headers(),
            params={
                "id": "eq." + str(record_id)
            },
            json=data,
            timeout=10
        )

        if r.status_code not in [200, 204]:
            return "Could not update record: " + r.text, 400

        return redirect("/teacher")

    # Get record
    r = requests.get(
        SUPABASE_URL + "/rest/v1/test_records",
        headers=db_headers(),
        params={
            "id": "eq." + str(record_id),
            "select": "id,test_name,marks,total_marks,test_date",
            "limit": 1
        },
        timeout=10
    )

    if r.status_code != 200:
        return "Database Error: " + r.text, 500

    records = r.json()

    if not records:
        return "Record not found", 404

    record = records[0]

    return f"""
    <!DOCTYPE html>
    <html>

    <head>

        <title>Edit Test Record</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

    </head>

    <body>

        <h1>✏️ Edit Test Record</h1>

        <form method="POST">

            <label>Test Name</label><br>

            <input
                type="text"
                name="test_name"
                value="{record["test_name"]}"
                required
            >

            <br><br>

            <label>Marks</label><br>

            <input
                type="number"
                name="marks"
                value="{record["marks"]}"
                min="0"
                step="1"
                required
            >

            <br><br>

            <label>Total Marks</label><br>

            <input
                type="number"
                name="total_marks"
                value="{record["total_marks"]}"
                min="1"
                step="1"
                required
            >

            <br><br>

            <label>Date</label><br>

            <input
                type="date"
                name="test_date"
                value="{record["test_date"]}"
                required
            >

            <br><br>

            <button type="submit">
                💾 Save Changes
            </button>

        </form>

        <br>

        <a href="/teacher">
            ← Back to Teacher Dashboard
        </a>

    </body>

    </html>
    """
@app.route("/teacher/delete-record/<int:record_id>", methods=["POST"])
def teacher_delete_record(record_id):

    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "teacher":
        return "Access Denied", 403

    r = requests.delete(
        SUPABASE_URL + "/rest/v1/test_records",
        headers=db_headers(),
        params={
            "id": "eq." + str(record_id)
        },
        timeout=10
    )

    if r.status_code not in [200, 204]:
        return "Could not delete record: " + r.text, 400

    return redirect("/teacher")
@app.route("/student")
def student():
    if "user_id" not in session:
        return redirect("/")

    if session.get("role") != "student":
        return "Access Denied", 403

    student_id = session["user_id"]

    # Get only logged-in student's records
    records_response = requests.get(
        SUPABASE_URL + "/rest/v1/test_records",
        headers=db_headers(),
        params={
            "student_id": "eq." + str(student_id),
            "select": "id,subject_id,test_name,marks,total_marks,test_date",
            "order": "test_date.desc"
        },
        timeout=10
    )

    if records_response.status_code != 200:
        return "Database Error: " + records_response.text, 500

    records = records_response.json()

    # Get subjects
    subjects_response = requests.get(
        SUPABASE_URL + "/rest/v1/subjects",
        headers=db_headers(),
        params={
            "select": "id,name"
        },
        timeout=10
    )

    if subjects_response.status_code != 200:
        return "Database Error: " + subjects_response.text, 500

    subjects = subjects_response.json()

    subject_names = {
        str(subject["id"]): subject["name"]
        for subject in subjects
    }

    rows = ""

    total_obtained = 0
    total_marks = 0

    for record in records:

        subject_name = subject_names.get(
            str(record["subject_id"]),
            "Unknown Subject"
        )

        marks = record["marks"]
        maximum = record["total_marks"]

        total_obtained += marks
        total_marks += maximum

        percentage = 0

        if maximum:
            percentage = round((marks / maximum) * 100, 2)

        rows += f"""
        <tr>
            <td>{subject_name}</td>
            <td>{record["test_name"]}</td>
            <td>{marks}/{maximum}</td>
            <td>{percentage}%</td>
            <td>{record["test_date"]}</td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="5">
                No test records found.
            </td>
        </tr>
        """

    overall_percentage = 0

    if total_marks > 0:
        overall_percentage = round(
            (total_obtained / total_marks) * 100,
            2
        )

    return f"""
    <!DOCTYPE html>
    <html>

    <head>

        <title>Student Dashboard</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <style>

            body {{
                font-family: Arial;
                background: #f2f5f9;
                padding: 15px;
            }}

            .box {{
                max-width: 1000px;
                margin: auto;
                background: white;
                padding: 20px;
                border-radius: 15px;
            }}

            .card {{
                background: #f1f5f9;
                padding: 15px;
                margin: 10px 0;
                border-radius: 10px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}

            th, td {{
                border: 1px solid #ccc;
                padding: 10px;
                text-align: left;
            }}

            th {{
                background: #2563eb;
                color: white;
            }}

            @media(max-width:600px) {{

                table {{
                    font-size: 13px;
                }}

                th, td {{
                    padding: 7px;
                }}

            }}

        </style>

    </head>

    <body>

    <div class="box">

        <h1>🎓 Student Dashboard</h1>

        <h3>
            Welcome, {session["name"]}
        </h3>

        <p>
            📧 {session["email"]}
        </p>

        <hr>

        <div class="card">

            <h2>📊 My Result</h2>

            <p>
                <b>Total Marks:</b>
                {total_obtained}/{total_marks}
            </p>

            <p>
                <b>Overall Percentage:</b>
                {overall_percentage}%
            </p>

        </div>

        <hr>

        <h2>📚 My Test Records</h2>

        <table>

            <tr>
                <th>Subject</th>
                <th>Test</th>
                <th>Marks</th>
                <th>Percentage</th>
                <th>Date</th>
            </tr>

            {rows}

        </table>

        <br>

        <a href="/logout">
            🚪 Logout
        </a>

    </div>

    </body>

    </html>
    """


@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")

    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>College Test Record | Login</title>

    <style>

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            min-height: 100vh;
            font-family: Arial, sans-serif;
            background:
                radial-gradient(circle at 20% 20%, #123c68 0%, transparent 35%),
                radial-gradient(circle at 80% 80%, #30145c 0%, transparent 35%),
                #050914;

            color: white;
            display: flex;
            align-items: center;
            justify-content: center;

            overflow: hidden;
        }

        /* Futuristic grid */

        body::before {
            content: "";
            position: fixed;
            inset: 0;

            background-image:
                linear-gradient(
                    rgba(0, 200, 255, 0.05) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(0, 200, 255, 0.05) 1px,
                    transparent 1px
                );

            background-size: 45px 45px;

            animation: gridMove 15s linear infinite;

            pointer-events: none;
        }

        @keyframes gridMove {
            from {
                transform: translateY(0);
            }

            to {
                transform: translateY(45px);
            }
        }

        /* Glow circles */

        .glow {
            position: fixed;
            width: 300px;
            height: 300px;

            border-radius: 50%;

            filter: blur(90px);

            opacity: 0.35;

            pointer-events: none;
        }

        .glow.one {
            background: #00d9ff;
            top: -100px;
            left: -100px;
        }

        .glow.two {
            background: #8b5cf6;
            bottom: -100px;
            right: -100px;
        }

        /* Main container */

        .login-container {
            width: 100%;
            max-width: 430px;

            padding: 20px;

            position: relative;
            z-index: 2;
        }

        /* Glass card */

        .login-card {
            padding: 38px 32px;

            border-radius: 24px;

            background:
                rgba(255, 255, 255, 0.07);

            border:
                1px solid rgba(255, 255, 255, 0.15);

            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);

            box-shadow:
                0 0 40px rgba(0, 200, 255, 0.12),
                inset 0 0 30px rgba(255, 255, 255, 0.02);

            animation: cardAppear 0.8s ease;
        }

        @keyframes cardAppear {
            from {
                opacity: 0;
                transform: translateY(30px) scale(0.97);
            }

            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        /* Logo */

        .logo {
            width: 75px;
            height: 75px;

            margin: 0 auto 20px;

            border-radius: 22px;

            display: flex;
            align-items: center;
            justify-content: center;

            font-size: 35px;

            background:
                linear-gradient(
                    135deg,
                    #00d9ff,
                    #6366f1
                );

            box-shadow:
                0 0 30px rgba(0, 217, 255, 0.4);

            animation: logoGlow 3s ease-in-out infinite;
        }

        @keyframes logoGlow {
            0%, 100% {
                box-shadow:
                    0 0 20px rgba(0, 217, 255, 0.35);
            }

            50% {
                box-shadow:
                    0 0 40px rgba(99, 102, 241, 0.6);
            }
        }

        h1 {
            text-align: center;

            font-size: 27px;

            margin-bottom: 8px;

            letter-spacing: 0.5px;
        }

        .subtitle {
            text-align: center;

            color: #9caec2;

            font-size: 14px;

            margin-bottom: 30px;
        }

        /* Input */

        .input-group {
            margin-bottom: 18px;
        }

        .input-group label {
            display: block;

            font-size: 13px;

            color: #b8c7d9;

            margin-bottom: 8px;
        }

        .input-wrapper {
            position: relative;
        }

        .input-icon {
            position: absolute;

            left: 15px;
            top: 50%;

            transform: translateY(-50%);

            font-size: 17px;

            opacity: 0.7;
        }

        input {
            width: 100%;

            padding: 14px 15px 14px 45px;

            border-radius: 12px;

            border:
                1px solid rgba(255, 255, 255, 0.12);

            background:
                rgba(0, 0, 0, 0.22);

            color: white;

            outline: none;

            font-size: 15px;

            transition: 0.3s;
        }

        input::placeholder {
            color: #718096;
        }

        input:focus {
            border-color: #00d9ff;

            box-shadow:
                0 0 15px rgba(0, 217, 255, 0.15);

            background:
                rgba(0, 0, 0, 0.32);
        }

        /* Login button */

        .login-button {
            width: 100%;

            padding: 14px;

            margin-top: 8px;

            border: none;

            border-radius: 12px;

            background:
                linear-gradient(
                    135deg,
                    #00b8e6,
                    #6366f1
                );

            color: white;

            font-size: 16px;

            font-weight: bold;

            cursor: pointer;

            transition: 0.3s;

            box-shadow:
                0 8px 25px rgba(0, 180, 230, 0.2);
        }

        .login-button:hover {
            transform: translateY(-2px);

            box-shadow:
                0 12px 35px rgba(0, 217, 255, 0.35);
        }

        .login-button:active {
            transform: scale(0.98);
        }

        /* Footer */

        .footer {
            text-align: center;

            margin-top: 25px;

            color: #65758b;

            font-size: 12px;
        }

        .status {
            display: flex;

            align-items: center;

            justify-content: center;

            gap: 7px;

            margin-top: 10px;

            color: #7f91a7;

            font-size: 11px;
        }

        .status-dot {
            width: 7px;
            height: 7px;

            border-radius: 50%;

            background: #22c55e;

            box-shadow:
                0 0 10px #22c55e;
        }

        /* Mobile */

        @media (max-width: 480px) {

            .login-container {
                padding: 15px;
            }

            .login-card {
                padding: 32px 22px;

                border-radius: 20px;
            }

            h1 {
                font-size: 24px;
            }

            .logo {
                width: 68px;
                height: 68px;

                font-size: 30px;
            }
        }

    </style>
</head>

<body>

    <div class="glow one"></div>
    <div class="glow two"></div>

    <div class="login-container">

        <div class="login-card">

            <div class="logo">
                🎓
            </div>

            <h1>
                College Test Record
            </h1>

            <p class="subtitle">
                Smart Academic Management System
            </p>

            <form method="POST" action="/login">

                <div class="input-group">

                    <label>
                        Email Address
                    </label>

                    <div class="input-wrapper">

                        <span class="input-icon">
                            ✉️
                        </span>

                        <input
                            type="email"
                            name="email"
                            placeholder="Enter your email"
                            required
                        >

                    </div>

                </div>

                <div class="input-group">

                    <label>
                        Password
                    </label>

                    <div class="input-wrapper">

                        <span class="input-icon">
                            🔐
                        </span>

                        <input
                            type="password"
                            name="password"
                            placeholder="Enter your password"
                            required
                        >

                    </div>

                </div>

                <button
                    type="submit"
                    class="login-button">

                    🚀 Login to Dashboard

                </button>

            </form>

            <div class="status">

                <span class="status-dot"></span>

                System Online

            </div>

            <div class="footer">

                College Test & Exam Record Management System
                <br><br>
                Secure • Smart • Connected

            </div>

        </div>

    </div>

</body>
</html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)