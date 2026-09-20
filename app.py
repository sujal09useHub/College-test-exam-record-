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

    # =========================
    # GET USERS
    # =========================
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

    # =========================
    # GET SUBJECTS
    # =========================
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

    # =========================
    # SUBJECT ROWS
    # =========================
    subject_rows = ""

    for subject in subjects:

        subject_rows += f"""
        <tr>

            <td>
                <span class="subject-name">
                    📚 {subject["name"]}
                </span>
            </td>

            <td>

                <a
                    class="edit-btn"
                    href="/admin/edit-subject/{subject["id"]}"
                >
                    ✏️ Edit
                </a>

                <form
                    method="POST"
                    action="/admin/delete-subject/{subject["id"]}"
                    class="inline-form"
                    onsubmit="return confirm('Delete this subject?');"
                >

                    <button
                        type="submit"
                        class="delete-btn"
                    >
                        🗑️ Delete
                    </button>

                </form>

            </td>

        </tr>
        """

    if not subject_rows:

        subject_rows = """
        <tr>
            <td colspan="2" class="empty">
                📚 No subjects found.
            </td>
        </tr>
        """

    # =========================
    # USER ROWS
    # =========================
    rows = ""

    for user in users:

        role = user["role"]

        if role == "developer":
            role_class = "developer-role"
            role_icon = "👨‍💻"
        elif role == "teacher":
            role_class = "teacher-role"
            role_icon = "👨‍🏫"
        else:
            role_class = "student-role"
            role_icon = "🎓"

        rows += f"""
        <tr>

            <td>
                <div class="user-name">
                    {role_icon} {user["name"]}
                </div>
            </td>

            <td class="email">
                {user["email"]}
            </td>

            <td>

                <span class="role-badge {role_class}">
                    {role}
                </span>

            </td>

            <td>

                <form
                    method="POST"
                    action="/admin/delete-user"
                    class="inline-form"
                    onsubmit="return confirm('Delete this user?');"
                >

                    <input
                        type="hidden"
                        name="user_id"
                        value="{user["id"]}"
                    >

                    <button
                        type="submit"
                        class="delete-btn"
                    >
                        🗑️ Delete
                    </button>

                </form>

            </td>

        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="4" class="empty">
                👥 No users found.
            </td>
        </tr>
        """

    # =========================
    # COUNTS
    # =========================
    student_count = sum(
        1 for user in users
        if user["role"] == "student"
    )

    teacher_count = sum(
        1 for user in users
        if user["role"] == "teacher"
    )

    developer_count = sum(
        1 for user in users
        if user["role"] == "developer"
    )

    # =========================
    # FUTURISTIC ADMIN UI
    # =========================
    return f"""
<!DOCTYPE html>

<html>

<head>

    <title>Developer Dashboard | College Test System</title>

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <style>

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Arial,
                sans-serif;

            min-height: 100vh;

            color: #e8f4ff;

            background:
                radial-gradient(
                    circle at 10% 10%,
                    rgba(0, 229, 255, 0.14),
                    transparent 30%
                ),
                radial-gradient(
                    circle at 90% 10%,
                    rgba(139, 92, 246, 0.16),
                    transparent 32%
                ),
                radial-gradient(
                    circle at 50% 100%,
                    rgba(0, 140, 255, 0.10),
                    transparent 35%
                ),
                #050914;

            overflow-x: hidden;
        }}

        body::before {{
            content: "";

            position: fixed;

            inset: 0;

            pointer-events: none;

            background-image:
                linear-gradient(
                    rgba(255,255,255,0.025) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(255,255,255,0.025) 1px,
                    transparent 1px
                );

            background-size: 40px 40px;

            mask-image:
                linear-gradient(
                    to bottom,
                    black,
                    transparent
                );
        }}

        .container {{
            width: 94%;
            max-width: 1200px;

            margin: 25px auto;

            position: relative;
            z-index: 1;
        }}

        /* HEADER */

        .header {{
            display: flex;

            justify-content: space-between;
            align-items: center;

            gap: 20px;

            padding: 23px;

            margin-bottom: 20px;

            border-radius: 22px;

            border:
                1px solid rgba(255,255,255,0.09);

            background:
                rgba(8,18,35,0.72);

            backdrop-filter: blur(18px);

            box-shadow:
                0 0 40px rgba(0,200,255,0.07);
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .logo {{
            width: 56px;
            height: 56px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 17px;

            font-size: 27px;

            background:
                linear-gradient(
                    135deg,
                    rgba(0,229,255,0.16),
                    rgba(139,92,246,0.18)
                );

            border:
                1px solid rgba(0,229,255,0.30);

            box-shadow:
                0 0 25px rgba(0,229,255,0.15);
        }}

        .title {{
            font-size: 25px;
            font-weight: 800;

            background:
                linear-gradient(
                    90deg,
                    #ffffff,
                    #6eeaff
                );

            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .subtitle {{
            margin-top: 5px;

            color: #849bb2;

            font-size: 13px;
        }}

        .logout {{
            text-decoration: none;

            color: #ffabb4;

            padding: 10px 15px;

            border-radius: 11px;

            background:
                rgba(255,60,80,0.08);

            border:
                1px solid rgba(255,70,90,0.25);

            transition: 0.25s;
        }}

        .logout:hover {{
            background:
                rgba(255,60,80,0.18);
        }}

        /* WELCOME */

        .welcome {{
            color: #94a9bf;

            margin-bottom: 20px;
        }}

        .welcome strong {{
            color: #68e8ff;
        }}

        /* STATS */

        .stats {{
            display: grid;

            grid-template-columns:
                repeat(4, 1fr);

            gap: 14px;

            margin-bottom: 22px;
        }}

        .stat {{
            padding: 20px;

            border-radius: 18px;

            border:
                1px solid rgba(255,255,255,0.08);

            background:
                rgba(8,18,35,0.70);

            backdrop-filter: blur(15px);
        }}

        .stat-icon {{
            font-size: 22px;
            margin-bottom: 9px;
        }}

        .stat-number {{
            font-size: 27px;

            font-weight: 800;

            color: #ffffff;
        }}

        .stat-label {{
            margin-top: 4px;

            color: #7f95ac;

            font-size: 12px;
        }}

        /* CARDS */

        .card {{
            padding: 24px;

            margin-bottom: 20px;

            border-radius: 22px;

            border:
                1px solid rgba(255,255,255,0.08);

            background:
                rgba(8,18,35,0.72);

            backdrop-filter: blur(18px);

            box-shadow:
                0 15px 45px rgba(0,0,0,0.18);
        }}

        .section-title {{
            font-size: 20px;

            color: #ffffff;

            margin-bottom: 5px;
        }}

        .section-description {{
            color: #7f96ad;

            font-size: 13px;

            margin-bottom: 20px;
        }}

        /* ADD USER */

        .form-grid {{
            display: grid;

            grid-template-columns:
                repeat(2, 1fr);

            gap: 14px;
        }}

        .field {{
            display: flex;
            flex-direction: column;
        }}

        .field label {{
            color: #9ab0c6;

            font-size: 13px;

            margin-bottom: 7px;
        }}

        input,
        select {{
            width: 100%;

            padding: 13px;

            border-radius: 11px;

            outline: none;

            color: #eaf7ff;

            background:
                rgba(2,8,20,0.75);

            border:
                1px solid rgba(255,255,255,0.10);

            transition: 0.25s;
        }}

        input:focus,
        select:focus {{
            border-color: #24ddff;

            box-shadow:
                0 0 0 3px rgba(36,221,255,0.07);
        }}

        input::placeholder {{
            color: #596e83;
        }}

        select option {{
            background: #081224;
            color: white;
        }}

        .primary-btn {{
            width: 100%;

            margin-top: 16px;

            padding: 14px;

            border: none;

            border-radius: 12px;

            color: white;

            font-size: 15px;

            font-weight: 700;

            cursor: pointer;

            background:
                linear-gradient(
                    100deg,
                    #008cff,
                    #00d9ff,
                    #7c3aed
                );

            box-shadow:
                0 0 25px rgba(0,180,255,0.16);

            transition: 0.25s;
        }}

        .primary-btn:hover {{
            transform: translateY(-2px);

            box-shadow:
                0 0 35px rgba(0,200,255,0.27);
        }}

        /* TABLE */

        .table-wrapper {{
            width: 100%;

            overflow-x: auto;

            border-radius: 14px;

            border:
                1px solid rgba(255,255,255,0.07);
        }}

        table {{
            width: 100%;

            min-width: 650px;

            border-collapse: collapse;
        }}

        th {{
            padding: 14px;

            text-align: left;

            color: #7992ab;

            font-size: 11px;

            text-transform: uppercase;

            letter-spacing: 0.7px;

            background:
                rgba(0,229,255,0.045);

            border-bottom:
                1px solid rgba(255,255,255,0.08);
        }}

        td {{
            padding: 14px;

            color: #c7d6e6;

            font-size: 13px;

            border-bottom:
                1px solid rgba(255,255,255,0.05);
        }}

        tr:hover td {{
            background:
                rgba(0,229,255,0.03);
        }}

        .user-name {{
            color: #e8f6ff;

            font-weight: 600;
        }}

        .email {{
            color: #8da5bb;
        }}

        .role-badge {{
            display: inline-block;

            padding: 5px 9px;

            border-radius: 8px;

            font-size: 11px;

            font-weight: 700;

            text-transform: uppercase;
        }}

        .student-role {{
            color: #7de8ff;

            background:
                rgba(0,190,255,0.09);

            border:
                1px solid rgba(0,190,255,0.15);
        }}

        .teacher-role {{
            color: #bca4ff;

            background:
                rgba(139,92,246,0.10);

            border:
                1px solid rgba(139,92,246,0.16);
        }}

        .developer-role {{
            color: #7affbd;

            background:
                rgba(40,220,130,0.09);

            border:
                1px solid rgba(40,220,130,0.15);
        }}

        .subject-name {{
            color: #dceeff;

            font-weight: 600;
        }}

        .edit-btn {{
            display: inline-block;

            padding: 7px 10px;

            margin-right: 4px;

            border-radius: 8px;

            color: #83eaff;

            text-decoration: none;

            background:
                rgba(0,180,255,0.08);

            border:
                1px solid rgba(0,180,255,0.16);
        }}

        .edit-btn:hover {{
            background:
                rgba(0,180,255,0.17);
        }}

        .inline-form {{
            display: inline;
        }}

        .delete-btn {{
            padding: 7px 10px;

            border-radius: 8px;

            border:
                1px solid rgba(255,70,90,0.18);

            color: #ff9eaa;

            background:
                rgba(255,60,80,0.08);

            cursor: pointer;
        }}

        .delete-btn:hover {{
            background:
                rgba(255,60,80,0.18);
        }}

        .empty {{
            text-align: center;

            padding: 35px !important;

            color: #657b91;
        }}

        /* STATUS */

        .status {{
            display: flex;

            justify-content: center;
            align-items: center;

            gap: 7px;

            color: #657d94;

            font-size: 12px;

            margin: 18px 0;
        }}

        .status-dot {{
            width: 7px;
            height: 7px;

            border-radius: 50%;

            background: #35f29a;

            box-shadow:
                0 0 10px #35f29a;
        }}

        /* MOBILE */

        @media (max-width: 750px) {{

            .container {{
                width: 94%;

                margin: 15px auto;
            }}

            .header {{
                padding: 18px;

                align-items: flex-start;
            }}

            .title {{
                font-size: 20px;
            }}

            .logo {{
                width: 45px;
                height: 45px;

                font-size: 22px;
            }}

            .logout {{
                font-size: 12px;

                padding: 8px 10px;
            }}

            .stats {{
                grid-template-columns:
                    repeat(2, 1fr);
            }}

            .form-grid {{
                grid-template-columns: 1fr;
            }}

            .card {{
                padding: 18px;
            }}

        }}

        @media (max-width: 430px) {{

            .stats {{
                grid-template-columns: 1fr;
            }}

        }}

    </style>

</head>

<body>

<div class="container">

    <!-- HEADER -->

    <div class="header">

        <div class="brand">

            <div class="logo">
                👨‍💻
            </div>

            <div>

                <div class="title">
                    Developer Console
                </div>

                <div class="subtitle">
                    College Test & Exam Management System
                </div>

            </div>

        </div>

        <a
            href="/logout"
            class="logout"
        >
            🚪 Logout
        </a>

    </div>


    <!-- WELCOME -->

    <div class="welcome">

        Welcome back,
        <strong>{session["name"]}</strong>
        👋

    </div>


    <!-- STATS -->

    <div class="stats">

        <div class="stat">

            <div class="stat-icon">
                👥
            </div>

            <div class="stat-number">
                {len(users)}
            </div>

            <div class="stat-label">
                Total Users
            </div>

        </div>


        <div class="stat">

            <div class="stat-icon">
                🎓
            </div>

            <div class="stat-number">
                {student_count}
            </div>

            <div class="stat-label">
                Students
            </div>

        </div>


        <div class="stat">

            <div class="stat-icon">
                👨‍🏫
            </div>

            <div class="stat-number">
                {teacher_count}
            </div>

            <div class="stat-label">
                Teachers
            </div>

        </div>


        <div class="stat">

            <div class="stat-icon">
                📚
            </div>

            <div class="stat-number">
                {len(subjects)}
            </div>

            <div class="stat-label">
                Subjects
            </div>

        </div>

    </div>


    <!-- ADD USER -->

    <div class="card">

        <div class="section-title">
            ➕ Add Student / Teacher
        </div>

        <div class="section-description">
            Create a new account for the college system.
        </div>


        <form
            method="POST"
            action="/admin/add-user"
        >

            <div class="form-grid">


                <div class="field">

                    <label>
                        👤 Name
                    </label>

                    <input
                        name="name"
                        placeholder="Enter full name"
                        required
                    >

                </div>


                <div class="field">

                    <label>
                        📧 Email
                    </label>

                    <input
                        name="email"
                        type="email"
                        placeholder="Enter email address"
                        required
                    >

                </div>


                <div class="field">

                    <label>
                        🔐 Password
                    </label>

                    <input
                        name="password"
                        type="password"
            placeholder="Create password"
                        required
                    >

                </div>


                <div class="field">

                    <label>
                        🎯 Account Role
                    </label>

                    <select
                        name="role"
                        required
                    >

                        <option value="student">
                            🎓 Student
                        </option>

                        <option value="teacher">
                            👨‍🏫 Teacher
                        </option>

                    </select>

                </div>

            </div>


            <button
                type="submit"
                class="primary-btn"
            >
                ⚡ Create User Account
            </button>

        </form>

    </div>


    <!-- USERS -->

    <div class="card">

        <div class="section-title">
            👥 User Management
        </div>

        <div class="section-description">
            View and manage registered system users.
        </div>


        <div class="table-wrapper">

            <table>

                <thead>

                    <tr>

                        <th>
                            Name
                        </th>

                        <th>
                            Email
                        </th>

                        <th>
                            Role
                        </th>

                        <th>
                            Action
                        </th>

                    </tr>

                </thead>

                <tbody>

                    {rows}

                </tbody>

            </table>

        </div>

    </div>


    <!-- SUBJECTS -->

    <div class="card">

        <div class="section-title">
            📚 Subject Management
        </div>

        <div class="section-description">
            Add and manage subjects available in the system.
        </div>


        <form
            method="POST"
            action="/admin/add-subject"
        >

            <div class="field">

                <label>
                    📖 Subject Name
                </label>

                <input
                    type="text"
                    name="name"
                    placeholder="Enter Subject Name"
                    required
                >

            </div>


            <button
                type="submit"
                class="primary-btn"
            >
                ➕ Add Subject
            </button>

        </form>


        <br>


        <div class="table-wrapper">

            <table>

                <thead>

                    <tr>

                        <th>
                            Subject
                        </th>

                        <th>
                            Action
                        </th>

                    </tr>

                </thead>

                <tbody>

                    {subject_rows}

                </tbody>

            </table>

        </div>

    </div>


    <!-- SYSTEM STATUS -->

    <div class="status">

        <span class="status-dot"></span>

        Developer Console • System Online

    </div>

</div>

</body>

</html>
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
<!DOCTYPE html>
<html>

<head>

    <title>User Created | College Test System</title>

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <style>

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            min-height: 100vh;

            display: flex;
            align-items: center;
            justify-content: center;

            padding: 20px;

            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Arial,
                sans-serif;

            color: #eaf7ff;

            background:
                radial-gradient(
                    circle at 20% 20%,
                    rgba(0,229,255,0.14),
                    transparent 32%
                ),
                radial-gradient(
                    circle at 80% 20%,
                    rgba(139,92,246,0.16),
                    transparent 32%
                ),
                #050914;
        }

        body::before {
            content: "";

            position: fixed;
            inset: 0;

            pointer-events: none;

            background-image:
                linear-gradient(
                    rgba(255,255,255,0.025) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(255,255,255,0.025) 1px,
                    transparent 1px
                );

            background-size: 40px 40px;
        }

        .card {
            width: 100%;
            max-width: 480px;

            padding: 40px 28px;

            text-align: center;

            border-radius: 25px;

            border:
                1px solid rgba(255,255,255,0.10);

            background:
                rgba(8,18,35,0.78);

            backdrop-filter: blur(20px);

            box-shadow:
                0 20px 60px rgba(0,0,0,0.35),
                0 0 40px rgba(0,200,255,0.08);

            position: relative;
            z-index: 1;
        }

        .success-icon {
            width: 80px;
            height: 80px;

            margin: 0 auto 22px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 50%;

            font-size: 38px;

            background:
                rgba(40,220,130,0.10);

            border:
                1px solid rgba(40,220,130,0.30);

            box-shadow:
                0 0 35px rgba(40,220,130,0.16);
        }

        h1 {
            font-size: 25px;

            margin-bottom: 10px;

            color: #ffffff;
        }

        .message {
            color: #8fa7bd;

            font-size: 14px;

            line-height: 1.6;

            margin-bottom: 28px;
        }

        .button {
            display: inline-block;

            width: 100%;

            padding: 14px;

            border-radius: 13px;

            text-decoration: none;

            color: white;

            font-size: 15px;

            font-weight: 700;

            background:
                linear-gradient(
                    100deg,
                    #008cff,
                    #00d9ff,
                    #7c3aed
                );

            box-shadow:
                0 0 25px rgba(0,180,255,0.18);

            transition: 0.25s;
        }

        .button:hover {
            transform: translateY(-2px);

            box-shadow:
                0 0 35px rgba(0,200,255,0.30);
        }

        .status {
            display: flex;

            justify-content: center;
            align-items: center;

            gap: 7px;

            margin-top: 22px;

            color: #637b91;

            font-size: 12px;
        }

        .dot {
            width: 7px;
            height: 7px;

            border-radius: 50%;

            background: #35f29a;

            box-shadow:
                0 0 10px #35f29a;
        }

    </style>

</head>

<body>

    <div class="card">

        <div class="success-icon">
            ✓
        </div>

        <h1>
            User Created Successfully
        </h1>

        <div class="message">
            The new account has been successfully
            created in the college management system.
        </div>

        <a
            href="/admin"
            class="button"
        >
            ← Back to Developer Dashboard
        </a>

        <div class="status">

            <span class="dot"></span>

            Database Updated • System Online

        </div>

    </div>

</body>

</html>
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

    # =========================
    # GET STUDENTS
    # =========================
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

    # =========================
    # GET SUBJECTS
    # =========================
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

    # =========================
    # GET TEST RECORDS
    # =========================
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

    # =========================
    # STUDENT OPTIONS
    # =========================
    student_options = ""

    for student in students:
        student_options += f"""
        <option value="{student["id"]}">
            {student["name"]} - {student["email"]}
        </option>
        """

    # =========================
    # SUBJECT OPTIONS
    # =========================
    subject_options = ""

    for subject in subjects:
        subject_options += f"""
        <option value="{subject["id"]}">
            {subject["name"]}
        </option>
        """

    # =========================
    # LOOKUP DICTIONARIES
    # =========================
    student_names = {
        str(student["id"]): student["name"]
        for student in students
    }

    subject_names = {
        str(subject["id"]): subject["name"]
        for subject in subjects
    }

    # =========================
    # RECORD TABLE
    # =========================
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

            <td>
                <div class="student-name">
                    🎓 {student_name}
                </div>
            </td>

            <td>
                <span class="subject-tag">
                    📚 {subject_name}
                </span>
            </td>

            <td>
                📝 {record["test_name"]}
            </td>

            <td>
                <span class="marks">
                    {record["marks"]}/{record["total_marks"]}
                </span>
            </td>

            <td>
                📅 {record["test_date"]}
            </td>

            <td>

                <a
                    class="edit-btn"
                    href="/teacher/edit-record/{record["id"]}"
                >
                    ✏️ Edit
                </a>

                <form
                    method="POST"
                    action="/teacher/delete-record/{record["id"]}"
                    class="delete-form"
                    onsubmit="return confirm('Delete this test record?');"
                >

                    <button
                        type="submit"
                        class="delete-btn"
                    >
                        🗑️ Delete
                    </button>

                </form>

            </td>

        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="6" class="empty">
                <div class="empty-icon">📊</div>
                <div>No test records yet.</div>
                <small>Add the first test record above.</small>
            </td>
        </tr>
        """

    # =========================
    # FUTURISTIC UI
    # =========================
    return f"""
<!DOCTYPE html>
<html>

<head>

    <title>Teacher Dashboard | College Test System</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <style>

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Arial,
                sans-serif;

            min-height: 100vh;

            color: #e8f4ff;

            background:
                radial-gradient(
                    circle at 10% 10%,
                    rgba(0, 229, 255, 0.13),
                    transparent 30%
                ),
                radial-gradient(
                    circle at 90% 20%,
                    rgba(139, 92, 246, 0.15),
                    transparent 32%
                ),
                radial-gradient(
                    circle at 50% 100%,
                    rgba(0, 153, 255, 0.10),
                    transparent 35%
                ),
                #050914;

            overflow-x: hidden;
        }}

        body::before {{
            content: "";

            position: fixed;

            inset: 0;

            pointer-events: none;

            background-image:
                linear-gradient(
                    rgba(255,255,255,0.025) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(255,255,255,0.025) 1px,
                    transparent 1px
                );

            background-size: 40px 40px;

            mask-image:
                linear-gradient(
                    to bottom,
                    black,
                    transparent
                );
        }}

        .container {{
            width: 94%;
            max-width: 1250px;

            margin: 30px auto;

            position: relative;
            z-index: 1;
        }}

        /* ================= HEADER ================= */

        .header {{
            display: flex;

            justify-content: space-between;
            align-items: center;

            gap: 20px;

            padding: 24px;

            margin-bottom: 22px;

            border: 1px solid rgba(255,255,255,0.09);

            border-radius: 22px;

            background:
                rgba(9, 18, 35, 0.72);

            backdrop-filter: blur(18px);

            box-shadow:
                0 0 35px rgba(0, 200, 255, 0.08);
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .logo {{
            width: 55px;
            height: 55px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 16px;

            font-size: 27px;

            background:
                linear-gradient(
                    135deg,
                    rgba(0,229,255,0.18),
                    rgba(139,92,246,0.18)
                );

            border: 1px solid rgba(0,229,255,0.35);

            box-shadow:
                0 0 25px rgba(0,229,255,0.18);
        }}

        .title {{
            font-size: 25px;
            font-weight: 800;

            background:
                linear-gradient(
                    90deg,
                    #ffffff,
                    #72eaff
                );

            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .subtitle {{
            margin-top: 4px;
            color: #8da4bd;
            font-size: 13px;
        }}

        .logout {{
            text-decoration: none;

            color: #ffb4b4;

            border: 1px solid rgba(255,80,80,0.3);

            background: rgba(255,60,60,0.08);

            padding: 10px 15px;

            border-radius: 12px;

            transition: 0.25s;
        }}

        .logout:hover {{
            background: rgba(255,60,60,0.18);

            box-shadow:
                0 0 18px rgba(255,60,60,0.15);
        }}

        /* ================= WELCOME ================= */

        .welcome {{
            margin-bottom: 20px;

            color: #a9bdd2;
        }}

        .welcome strong {{
            color: #65e8ff;
        }}

        /* ================= STATS ================= */

        .stats {{
            display: grid;

            grid-template-columns:
                repeat(3, 1fr);

            gap: 15px;

            margin-bottom: 22px;
        }}

        .stat {{
            padding: 20px;

            border-radius: 18px;

            border: 1px solid rgba(255,255,255,0.08);

            background:
                rgba(10,20,39,0.70);

            backdrop-filter: blur(15px);

            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.04);
        }}

        .stat-icon {{
            font-size: 22px;
            margin-bottom: 10px;
        }}

        .stat-number {{
            font-size: 28px;
            font-weight: 800;

            color: #ffffff;
        }}

        .stat-label {{
            color: #8298af;
            font-size: 13px;
            margin-top: 4px;
        }}

        /* ================= ADD TEST ================= */

        .card {{
            padding: 25px;

            margin-bottom: 22px;

            border-radius: 22px;

            border:
                1px solid rgba(255,255,255,0.09);

            background:
                rgba(8,18,35,0.72);

            backdrop-filter: blur(18px);

            box-shadow:
                0 15px 45px rgba(0,0,0,0.20);
        }}

        .section-title {{
            font-size: 20px;

            margin-bottom: 5px;

            color: #ffffff;
        }}

        .section-description {{
            color: #8197ae;
            font-size: 13px;

            margin-bottom: 22px;
        }}

        .form-grid {{
            display: grid;

            grid-template-columns:
                repeat(2, 1fr);

            gap: 15px;
        }}

        .field {{
            display: flex;
            flex-direction: column;
        }}

        .field label {{
            color: #9db3ca;

            font-size: 13px;

            margin-bottom: 7px;
        }}

        input,
        select {{
            width: 100%;

            padding: 13px 14px;

            border-radius: 12px;

            border:
                1px solid rgba(255,255,255,0.10);

            background:
                rgba(2,8,20,0.75);

            color: #eaf7ff;

            outline: none;

            transition: 0.25s;
        }}

        input::placeholder {{
            color: #586c82;
        }}

        input:focus,
        select:focus {{
            border-color: #27dfff;

            box-shadow:
                0 0 0 3px rgba(39,223,255,0.08),
                0 0 20px rgba(39,223,255,0.10);
        }}

        select option {{
            background: #081224;
            color: white;
        }}

        .add-btn {{
            width: 100%;

            margin-top: 18px;

            padding: 14px;

            border: none;

            border-radius: 13px;

            color: white;

            font-size: 15px;
            font-weight: 700;

            cursor: pointer;

            background:
                linear-gradient(
                    100deg,
                    #008cff,
                    #00d9ff,
                    #7c3aed
                );

            box-shadow:
                0 0 25px rgba(0,180,255,0.18);

            transition: 0.25s;
        }}

        .add-btn:hover {{
            transform: translateY(-2px);

            box-shadow:
                0 0 35px rgba(0,200,255,0.30);
        }}

        /* ================= RECORDS ================= */

        .table-wrapper {{
            width: 100%;

            overflow-x: auto;

            border-radius: 15px;

            border:
                1px solid rgba(255,255,255,0.07);
        }}

        table {{
            width: 100%;

            min-width: 850px;

            border-collapse: collapse;
        }}

        th {{
            padding: 15px;

            text-align: left;

            font-size: 12px;

            color: #7f9bb6;

            text-transform: uppercase;

            letter-spacing: 0.6px;

            background:
                rgba(0,229,255,0.045);

            border-bottom:
                1px solid rgba(255,255,255,0.08);
        }}

        td {{
            padding: 14px 15px;

            color: #c8d7e8;

            font-size: 13px;

            border-bottom:
                1px solid rgba(255,255,255,0.055);
        }}

        tr:hover td {{
            background:
                rgba(0,229,255,0.035);
        }}

        .student-name {{
            color: #e8f6ff;
            font-weight: 600;
        }}

        .subject-tag {{
            display: inline-block;

            padding: 5px 9px;

            border-radius: 8px;

            color: #8eeeff;

            background:
                rgba(0,200,255,0.08);

            border:
                1px solid rgba(0,200,255,0.13);
        }}

        .marks {{
            color: #7cf4b4;

            font-weight: 700;
        }}

        .edit-btn {{
            display: inline-block;

            text-decoration: none;

            padding: 7px 10px;

            margin-right: 5px;

            border-radius: 8px;

            color: #8eeeff;

            background:
                rgba(0,180,255,0.09);

            border:
                1px solid rgba(0,180,255,0.18);

            transition: 0.2s;
        }}

        .edit-btn:hover {{
            background:
                rgba(0,180,255,0.18);
        }}

        .delete-form {{
            display: inline;
        }}

        .delete-btn {{
            padding: 7px 10px;

            border-radius: 8px;

            border:
                1px solid rgba(255,70,90,0.18);

            color: #ff9da8;

            background:
                rgba(255,60,80,0.08);

            cursor: pointer;

            transition: 0.2s;
        }}

        .delete-btn:hover {{
            background:
                rgba(255,60,80,0.18);
        }}

        .empty {{
            text-align: center;

            padding: 45px !important;

            color: #71879d;
        }}

        .empty-icon {{
            font-size: 35px;
            margin-bottom: 10px;
        }}

        .empty small {{
            display: block;
            margin-top: 7px;
            color: #53687d;
        }}

        /* ================= STATUS ================= */

        .status {{
            display: flex;

            justify-content: center;
            align-items: center;

            gap: 7px;

            margin-top: 18px;

            color: #6e879e;

            font-size: 12px;
        }}

        .status-dot {{
            width: 7px;
            height: 7px;

            border-radius: 50%;

            background: #35f29a;

            box-shadow:
                0 0 10px #35f29a;
        }}

        /* ================= MOBILE ================= */

        @media (max-width: 700px) {{

            .container {{
                width: 94%;
                margin: 15px auto;
            }}

            .header {{
                padding: 18px;

                align-items: flex-start;
            }}

            .title {{
                font-size: 20px;
            }}

            .logo {{
                width: 45px;
                height: 45px;
                font-size: 22px;
            }}

            .logout {{
                font-size: 12px;
                padding: 8px 10px;
            }}

            .stats {{
                grid-template-columns: 1fr;
            }}

            .form-grid {{
                grid-template-columns: 1fr;
            }}

            .card {{
                padding: 18px;
            }}

        }}

    </style>

</head>

<body>

<div class="container">

    <!-- HEADER -->

    <div class="header">

        <div class="brand">

            <div class="logo">
                👨‍🏫
            </div>

            <div>

                <div class="title">
                    Teacher Portal
                </div>

                <div class="subtitle">
                    College Test & Exam Management System
                </div>

            </div>

        </div>

        <a
            class="logout"
            href="/logout"
        >
            🚪 Logout
        </a>

    </div>


    <!-- WELCOME -->

    <div class="welcome">
        Welcome back,
        <strong>{session["name"]}</strong>
        👋
    </div>


    <!-- STATS -->

    <div class="stats">

        <div class="stat">

            <div class="stat-icon">
                👨‍🎓
            </div>

            <div class="stat-number">
                {len(students)}
            </div>

            <div class="stat-label">
                Total Students
            </div>

        </div>


        <div class="stat">

            <div class="stat-icon">
                📚
            </div>

            <div class="stat-number">
                {len(subjects)}
            </div>

            <div class="stat-label">
                Total Subjects
            </div>

        </div>


        <div class="stat">

            <div class="stat-icon">
                📊
            </div>

            <div class="stat-number">
                {len(records)}
            </div>

            <div class="stat-label">
                Test Records
            </div>

        </div>

    </div>


    <!-- ADD TEST -->

    <div class="card">

        <div class="section-title">
            ➕ Add Test Marks
        </div>

        <div class="section-description">
            Create a new test record for a student.
        </div>


        <form
            method="POST"
            action="/teacher/add-record"
        >

            <div class="form-grid">


                <div class="field">

                    <label>
                        🎓 Student
                    </label>

                    <select
                        name="student_id"
                        required
                    >

                        <option value="">
                            Select Student
                        </option>

                        {student_options}

                    </select>

                </div>


                <div class="field">

                    <label>
                        📚 Subject
                    </label>

                    <select
                        name="subject_id"
                        required
                    >

                        <option value="">
                            Select Subject
                        </option>

                        {subject_options}

                    </select>

                </div>


                <div class="field">

                    <label>
                        📝 Test Name
                    </label>

                    <input
                        type="text"
                        name="test_name"
       placeholder="Example: Unit Test 1"
                        required
                    >

                </div>


                <div class="field">

                    <label>
                        📅 Test Date
                    </label>

                    <input
                        type="date"
                        name="test_date"
                        required
                    >

                </div>


                <div class="field">

                    <label>
                        📊 Marks Obtained
                    </label>

                    <input
                        type="number"
                        name="marks"
                        min="0"
                        step="1"
                        placeholder="Example: 42"
                        required
                    >

                </div>


                <div class="field">

                    <label>
                        📋 Total Marks
                    </label>

                    <input
                        type="number"
                        name="total_marks"
                        min="1"
                        step="1"
                        placeholder="Example: 50"
                        required
                    >

                </div>

            </div>


            <button
                type="submit"
                class="add-btn"
            >
                ⚡ Add Test Record
            </button>

        </form>

    </div>


    <!-- RECORDS -->

    <div class="card">

        <div class="section-title">
            📊 All Student Test Records
        </div>

        <div class="section-description">
            View and manage test performance records.
        </div>


        <div class="table-wrapper">

            <table>

                <thead>

                    <tr>

                        <th>
                            Student
                        </th>

                        <th>
                            Subject
                        </th>

                        <th>
                            Test
                        </th>

                        <th>
                            Marks
                        </th>

                        <th>
                            Date
                        </th>

                        <th>
                            Actions
                        </th>

                    </tr>

                </thead>


                <tbody>

                    {rows}

                </tbody>

            </table>

        </div>

    </div>


    <div class="status">

        <span class="status-dot"></span>

        College Test System • System Online

    </div>


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
<!DOCTYPE html>
<html>

<head>

    <title>Test Added | College Test System</title>

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <style>

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            min-height: 100vh;

            display: flex;
            align-items: center;
            justify-content: center;

            padding: 20px;

            font-family:
                Inter,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                Arial,
                sans-serif;

            color: #eaf7ff;

            background:
                radial-gradient(
                    circle at 20% 20%,
                    rgba(0,229,255,0.14),
                    transparent 32%
                ),
                radial-gradient(
                    circle at 80% 20%,
                    rgba(139,92,246,0.16),
                    transparent 32%
                ),
                #050914;
        }

        body::before {
            content: "";

            position: fixed;

            inset: 0;

            pointer-events: none;

            background-image:
                linear-gradient(
                    rgba(255,255,255,0.025) 1px,
                    transparent 1px
                ),
                linear-gradient(
                    90deg,
                    rgba(255,255,255,0.025) 1px,
                    transparent 1px
                );

            background-size: 40px 40px;
        }

        .card {
            width: 100%;
            max-width: 480px;

            padding: 40px 28px;

            text-align: center;

            border-radius: 25px;

            border:
                1px solid rgba(255,255,255,0.10);

            background:
                rgba(8,18,35,0.78);

            backdrop-filter: blur(20px);

            box-shadow:
                0 20px 60px rgba(0,0,0,0.35),
                0 0 40px rgba(0,200,255,0.08);

            position: relative;
            z-index: 1;
        }

        .success-icon {
            width: 80px;
            height: 80px;

            margin: 0 auto 22px;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 50%;

            font-size: 38px;

            background:
                rgba(40,220,130,0.10);

            border:
                1px solid rgba(40,220,130,0.30);

            box-shadow:
                0 0 35px rgba(40,220,130,0.16);
        }

        h1 {
            font-size: 25px;

            margin-bottom: 10px;

            color: #ffffff;
        }

        .message {
            color: #8fa7bd;

            font-size: 14px;

            line-height: 1.6;

            margin-bottom: 28px;
        }

        .button {
            display: inline-block;

            width: 100%;

            padding: 14px;

            border-radius: 13px;

            text-decoration: none;

            color: white;

            font-size: 15px;

            font-weight: 700;

            background:
                linear-gradient(
                    100deg,
                    #008cff,
                    #00d9ff,
                    #7c3aed
                );

            box-shadow:
                0 0 25px rgba(0,180,255,0.18);

            transition: 0.25s;
        }

        .button:hover {
            transform: translateY(-2px);

            box-shadow:
                0 0 35px rgba(0,200,255,0.30);
        }

        .status {
            display: flex;

            justify-content: center;
            align-items: center;

            gap: 7px;

            margin-top: 22px;

            color: #637b91;

            font-size: 12px;
        }

        .dot {
            width: 7px;
            height: 7px;

            border-radius: 50%;

            background: #35f29a;

            box-shadow:
                0 0 10px #35f29a;
        }

    </style>

</head>

<body>

    <div class="card">

        <div class="success-icon">
            ✓
        </div>

        <h1>
            Test Record Added
        </h1>

        <div class="message">
            The test record has been successfully
            saved to the college examination system.
        </div>

        <a
            href="/teacher"
            class="button"
        >
            ← Back to Teacher Dashboard
        </a>

        <div class="status">

            <span class="dot"></span>

            Database Updated • System Online

        </div>

    </div>

</body>

</html>
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

    total_obtained = 0
    total_marks = 0
    test_count = len(records)

    rows = ""

    # Subject performance data
    subject_stats = {}

    for record in records:

        subject_id = str(record["subject_id"])

        subject_name = subject_names.get(
            subject_id,
            "Unknown Subject"
        )

        marks = record["marks"]
        maximum = record["total_marks"]

        total_obtained += marks
        total_marks += maximum

        percentage = 0

        if maximum:
            percentage = round(
                (marks / maximum) * 100,
                2
            )

        # Subject statistics
        if subject_name not in subject_stats:
            subject_stats[subject_name] = {
                "obtained": 0,
                "total": 0
            }

        subject_stats[subject_name]["obtained"] += marks
        subject_stats[subject_name]["total"] += maximum

        rows += f"""
        <div class="test-card">

            <div class="test-main">

                <div>
                    <div class="test-name">
                        {record["test_name"]}
                    </div>

                    <div class="test-subject">
                        📚 {subject_name}
                    </div>
                </div>

                <div class="test-score">
                    {percentage}%
                </div>

            </div>

            <div class="test-info">

                <span>
                    📊 {marks}/{maximum}
                </span>

                <span>
                    📅 {record["test_date"]}
                </span>

            </div>

            <div class="mini-progress">
                <div
                    class="mini-progress-fill"
                    style="width:{min(percentage, 100)}%;">
                </div>
            </div>

        </div>
        """

    if not rows:
        rows = """
        <div class="empty-state">

            <div class="empty-icon">📭</div>

            <h3>No Test Records Yet</h3>

            <p>
                Your test results will appear here
                when your teacher adds them.
            </p>

        </div>
        """

    # Overall percentage
    overall_percentage = 0

    if total_marks > 0:
        overall_percentage = round(
            (total_obtained / total_marks) * 100,
            2
        )

    # Subject cards
    subject_cards = ""

    for subject_name, data in subject_stats.items():

        subject_percentage = 0

        if data["total"] > 0:
            subject_percentage = round(
                (data["obtained"] / data["total"]) * 100,
                1
            )

        subject_cards += f"""
        <div class="subject-card">

            <div class="subject-top">

                <div class="subject-icon">
                    📚
                </div>

                <div>
                    <div class="subject-name">
                        {subject_name}
                    </div>

                    <div class="subject-marks">
                        {data["obtained"]}/{data["total"]} marks
                    </div>
                </div>

            </div>

            <div class="subject-percent">
                {subject_percentage}%
            </div>

            <div class="progress">
                <div
                    class="progress-fill"
                    style="width:{min(subject_percentage, 100)}%;">
                </div>
            </div>

        </div>
        """

    if not subject_cards:
        subject_cards = """
        <div class="empty-subject">
            No subject performance available yet.
        </div>
        """

    return f"""
<!DOCTYPE html>
<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Student Dashboard | College Test Record</title>

    <style>

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{

            font-family:
                Arial,
                Helvetica,
                sans-serif;

            min-height: 100vh;

            color: white;

            background:
                radial-gradient(
                    circle at 10% 10%,
                    #123b62 0%,
                    transparent 32%
                ),

                radial-gradient(
                    circle at 90% 80%,
                    #32145c 0%,
                    transparent 35%
                ),

                #050914;

            overflow-x: hidden;
        }}

        body::before {{

            content: "";

            position: fixed;

            inset: 0;

            background-image:

                linear-gradient(
                    rgba(0, 200, 255, 0.035) 1px,
                    transparent 1px
                ),

                linear-gradient(
                    90deg,
                    rgba(0, 200, 255, 0.035) 1px,
                    transparent 1px
                );

            background-size: 45px 45px;

            pointer-events: none;

            z-index: 0;
        }}

        .container {{

            position: relative;

            z-index: 1;

            width: 100%;

            max-width: 1150px;

            margin: auto;

            padding: 22px;
        }}

        /* HEADER */

        .header {{

            display: flex;

            justify-content: space-between;

            align-items: center;

            padding: 18px 22px;

            margin-bottom: 25px;

            border-radius: 20px;

            background:
                rgba(255,255,255,0.07);

            border:
                1px solid rgba(255,255,255,0.12);

            backdrop-filter: blur(18px);

            box-shadow:
                0 10px 35px rgba(0,0,0,0.25);
        }}

        .brand {{

            display: flex;

            align-items: center;

            gap: 12px;
        }}

        .brand-icon {{

            width: 48px;
            height: 48px;

            border-radius: 14px;

            display: flex;

            align-items: center;

            justify-content: center;

            font-size: 24px;

            background:
                linear-gradient(
                    135deg,
                    #00c8ff,
                    #6366f1
                );

            box-shadow:
                0 0 25px
                rgba(0,200,255,0.25);
        }}

        .brand-title {{

            font-size: 18px;

            font-weight: bold;
        }}

        .brand-subtitle {{

            font-size: 11px;

            color: #8293aa;

            margin-top: 3px;
        }}

        .logout {{

            text-decoration: none;

            color: #d8e5f2;

            padding: 10px 15px;

            border-radius: 10px;

            border:
                1px solid rgba(255,255,255,0.12);

            background:
                rgba(255,255,255,0.05);

            transition: 0.3s;
        }}

        .logout:hover {{

            background:
                rgba(255,70,100,0.15);

            border-color:
                rgba(255,100,120,0.4);
        }}

        /* WELCOME */

        .welcome {{

            margin: 25px 0;
        }}

        .welcome-small {{

            color: #7e91a9;

            font-size: 13px;

            margin-bottom: 7px;
        }}

        .welcome h1 {{

            font-size: 32px;

            margin-bottom: 8px;
        }}

        .welcome p {{

            color: #91a2b7;

            font-size: 14px;
        }}

        /* STAT CARDS */

        .stats {{

            display: grid;

            grid-template-columns:
                repeat(3, 1fr);

            gap: 16px;

            margin-bottom: 25px;
        }}

        .stat-card {{

            padding: 22px;

            border-radius: 18px;

            background:
                rgba(255,255,255,0.065);

            border:
                1px solid rgba(255,255,255,0.11);

            backdrop-filter: blur(15px);

            transition: 0.3s;
        }}

        .stat-card:hover {{

            transform: translateY(-4px);

            border-color:
                rgba(0,210,255,0.35);

            box-shadow:
                0 10px 35px
                rgba(0,200,255,0.08);
        }}

        .stat-icon {{

            font-size: 22px;

            margin-bottom: 12px;
        }}

        .stat-label {{

            color: #8798ad;

            font-size: 12px;

            margin-bottom: 6px;
        }}

        .stat-value {{

            font-size: 27px;

            font-weight: bold;
        }}

        .stat-value span {{

            font-size: 13px;

            color: #7e90a7;

            font-weight: normal;
        }}

        /* PERFORMANCE */

        .section {{

            margin-top: 25px;
        }}

        .section-title {{

            font-size: 19px;

            margin-bottom: 14px;
        }}

        .performance-card {{

            display: flex;

            align-items: center;

            gap: 28px;

            padding: 25px;

            border-radius: 20px;

            background:
                rgba(255,255,255,0.065);

            border:
                1px solid rgba(255,255,255,0.11);

            backdrop-filter: blur(15px);
        }}

        .percentage-circle {{

            min-width: 130px;

            height: 130px;

            border-radius: 50%;

            display: flex;

            flex-direction: column;

            align-items: center;

            justify-content: center;

            background:
                radial-gradient(
                    circle,
                    #101a2b 55%,
                    transparent 56%
                );

            border:
                5px solid #00c8ff;

            box-shadow:
                0 0 25px
                rgba(0,200,255,0.25);
        }}

        .percentage-number {{

            font-size: 25px;

            font-weight: bold;
        }}

        .percentage-label {{

            color: #7f92a9;

            font-size: 11px;

            margin-top: 4px;
        }}

        .performance-info h3 {{

            font-size: 20px;

            margin-bottom: 8px;
        }}

        .performance-info p {{

            color: #8fa0b5;

            font-size: 13px;

            line-height: 1.6;
        }}

        /* SUBJECTS */

        .subjects {{

            display: grid;

            grid-template-columns:
                repeat(3, 1fr);

            gap: 15px;
        }}

        .subject-card {{

            padding: 18px;

            border-radius: 17px;

            background:
                rgba(255,255,255,0.055);

            border:
                1px solid rgba(255,255,255,0.10);

            transition: 0.3s;
        }}

        .subject-card:hover {{

            transform: translateY(-3px);

            border-color:
                rgba(99,102,241,0.4);
        }}

        .subject-top {{

            display: flex;

            align-items: center;

            gap: 12px;
        }}

        .subject-icon {{

            width: 42px;
            height: 42px;

            display: flex;

            align-items: center;

            justify-content: center;

            border-radius: 12px;

            background:
                rgba(0,200,255,0.1);

            font-size: 20px;
        }}

        .subject-name {{

            font-size: 14px;

            font-weight: bold;
        }}

        .subject-marks {{

            color: #778ba2;

            font-size: 11px;

            margin-top: 4px;
        }}

        .subject-percent {{

            font-size: 24px;

            font-weight: bold;

            margin: 18px 0 10px;
        }}

        .progress {{

            height: 6px;

            border-radius: 10px;

            background:
                rgba(255,255,255,0.08);

            overflow: hidden;
        }}

        .progress-fill {{

            height: 100%;

            border-radius: 10px;

            background:
                linear-gradient(
                    90deg,
                    #00c8ff,
                    #6366f1
                );

            box-shadow:
                0 0 10px
                rgba(0,200,255,0.4);
        }}

        /* TEST RECORDS */

        .test-list {{

            display: flex;

            flex-direction: column;

            gap: 12px;
        }}

        .test-card {{

            padding: 17px;

            border-radius: 15px;

            background:
                rgba(255,255,255,0.05);

            border:
                1px solid rgba(255,255,255,0.09);

            transition: 0.3s;
        }}

        .test-card:hover {{

            background:
                rgba(255,255,255,0.075);

            transform: translateX(3px);
        }}

        .test-main {{

            display: flex;

            justify-content: space-between;

            align-items: center;
        }}

        .test-name {{

            font-weight: bold;

            font-size: 14px;
        }}

        .test-subject {{

            color: #7d90a7;

            font-size: 11px;

            margin-top: 5px;
        }}

        .test-score {{

            font-size: 20px;

            font-weight: bold;

            color: #00d9ff;
        }}

        .test-info {{

            display: flex;

            gap: 18px;

            margin-top: 12px;

            color: #75889f;

            font-size: 11px;
        }}

        .mini-progress {{

            height: 4px;

            margin-top: 12px;

            background:
                rgba(255,255,255,0.07);

            border-radius: 10px;

            overflow: hidden;
        }}

        .mini-progress-fill {{

            height: 100%;

            background:
                linear-gradient(
                    90deg,
                    #00c8ff,
                    #6366f1
                );

            border-radius: 10px;
        }}

        /* EMPTY */

        .empty-state {{

            text-align: center;

            padding: 40px 20px;

            border-radius: 18px;

            background:
                rgba(255,255,255,0.04);

            border:
                1px dashed
                rgba(255,255,255,0.15);
        }}

        .empty-icon {{

            font-size: 35px;

            margin-bottom: 12px;
        }}

        .empty-state h3 {{

            margin-bottom: 7px;
        }}

        .empty-state p {{

            color: #778ba2;

            font-size: 13px;
        }}

        .empty-subject {{

            padding: 20px;

            color: #778ba2;
        }}

        /* FOOTER */

        .footer {{

            text-align: center;

            color: #566a82;

            font-size: 11px;

            padding: 30px 0 10px;
        }}

        /* MOBILE */

        @media(max-width: 750px) {{

            .container {{
                padding: 14px;
            }}

            .header {{
                padding: 14px;
            }}

            .brand-title {{
                font-size: 15px;
            }}

            .brand-subtitle {{
                display: none;
            }}

            .welcome h1 {{
                font-size: 25px;
            }}

            .stats {{
                grid-template-columns: 1fr;
            }}

            .subjects {{
                grid-template-columns: 1fr;
            }}

            .performance-card {{
                flex-direction: column;

                text-align: center;
            }}

            .percentage-circle {{
                min-width: 115px;
                height: 115px;
            }}

            .test-main {{
                align-items: flex-start;
            }}

            .test-score {{
                font-size: 18px;
            }}

            .logout {{
                padding: 8px 11px;

                font-size: 12px;
            }}
        }}

    </style>

</head>

<body>

<div class="container">

    <!-- HEADER -->

    <header class="header">

        <div class="brand">

            <div class="brand-icon">
                🎓
            </div>

            <div>

                <div class="brand-title">
                    College Test Record
                </div>

                <div class="brand-subtitle">
                    Smart Academic Management System
                </div>

            </div>

        </div>

        <a
            href="/logout"
            class="logout">

            🚪 Logout

        </a>

    </header>


    <!-- WELCOME -->

    <section class="welcome">

        <div class="welcome-small">
            STUDENT PORTAL
        </div>

        <h1>
            Welcome, {session["name"]} 👋
        </h1>

        <p>
            Track your academic performance and test results.
        </p>

    </section>


    <!-- STAT CARDS -->

    <section class="stats">

        <div class="stat-card">

            <div class="stat-icon">
                📝
            </div>

            <div class="stat-label">
                TOTAL TESTS
            </div>

            <div class="stat-value">
                {test_count}
            </div>

        </div>


        <div class="stat-card">

            <div class="stat-icon">
                📊
            </div>

            <div class="stat-label">
                TOTAL MARKS
            </div>

            <div class="stat-value">

                {total_obtained}

                <span>
                    / {total_marks}
                </span>

            </div>

        </div>


        <div class="stat-card">

            <div class="stat-icon">
                🎯
            </div>

            <div class="stat-label">
                OVERALL PERFORMANCE
            </div>

            <div class="stat-value">
                {overall_percentage}%
            </div>

        </div>

    </section>


    <!-- PERFORMANCE -->

    <section class="section">

        <div class="section-title">
            📈 Performance Overview
        </div>

        <div class="performance-card">

            <div class="percentage-circle">

                <div class="percentage-number">
                    {overall_percentage}%
                </div>

                <div class="percentage-label">
                    OVERALL
                </div>

            </div>

            <div class="performance-info">

                <h3>
                    Your Academic Progress
                </h3>

                <p>
                    You have scored
                    <b>{total_obtained}</b>
                    marks out of
                    <b>{total_marks}</b>
                    across
                    <b>{test_count}</b>
                    test(s).
                </p>

                <p style="margin-top:8px;">
                    Keep tracking your performance
                    and continue improving.
                </p>

            </div>

        </div>

    </section>


    <!-- SUBJECT PERFORMANCE -->

    <section class="section">

        <div class="section-title">
            📚 Subject Performance
        </div>

        <div class="subjects">

            {subject_cards}

        </div>

    </section>


    <!-- TEST RECORDS -->

    <section class="section">

        <div class="section-title">
            📝 Recent Test Records
        </div>

        <div class="test-list">

            {rows}

        </div>

    </section>


    <div class="footer">

        College Test & Exam Record Management System

        <br><br>

        Secure • Smart • Connected

    </div>

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