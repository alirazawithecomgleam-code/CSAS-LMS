import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "lms.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("LMS_SECRET_KEY", "change-this-demo-secret-before-deployment")
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "png", "jpg", "jpeg", "zip"}

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student','teacher')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        teacher_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        color TEXT NOT NULL DEFAULT 'blue'
    );
    CREATE TABLE IF NOT EXISTS enrollments (
        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        PRIMARY KEY(student_id, course_id)
    );
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        due_date TEXT NOT NULL,
        total_marks INTEGER NOT NULL DEFAULT 100,
        created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        text_answer TEXT NOT NULL DEFAULT '',
        file_name TEXT NOT NULL DEFAULT '',
        submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        marks REAL,
        feedback TEXT NOT NULL DEFAULT '',
        graded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        graded_at TEXT,
        UNIQUE(assignment_id, student_id)
    );
    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        file_name TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL DEFAULT '',
        uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        audience TEXT NOT NULL DEFAULT 'all',
        created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        day TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        room TEXT NOT NULL DEFAULT 'TBA'
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late')),
        marked_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        marked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(course_id, student_id, attendance_date)
    );
    """)
    user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                   ("Ayesha Khan", "student@learnspace.edu", generate_password_hash("Student123!"), "student"))
        db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                   ("Dr. Hamza Ali", "teacher@learnspace.edu", generate_password_hash("Teacher123!"), "teacher"))
        teacher_id = db.execute("SELECT id FROM users WHERE email='teacher@learnspace.edu'").fetchone()[0]
        student_id = db.execute("SELECT id FROM users WHERE email='student@learnspace.edu'").fetchone()[0]
    # Campus-specific seed data is idempotent and can be added to an existing demo database.
    teacher_specs = [
        ("Dr. Hafiz Muhammad Tahir", "tahir@csas.pu.edu.pk", "Tahir@2026", "BSTA-201", "Biostatistics-III (Statistical Inference)", "Statistical inference, estimation and hypothesis testing.", "blue"),
        ("Dr. Zulfiqar Ali", "zulfiqar@csas.pu.edu.pk", "Zulfiqar@2026", "BSTA-202", "Epidemiology", "Study of disease patterns and population health.", "teal"),
        ("Ms. Minahil Sada Hussain", "minahil@csas.pu.edu.pk", "Minahil@2026", "GENG-201", "Expository Writing", "Academic writing, argument and clear communication.", "violet"),
        ("Ms. Fatima Shahzad", "fatima.shahzad@csas.pu.edu.pk", "FatimaS@2026", "GICT-201", "Applications of Information and Communication Technologies", "Digital tools and ICT applications for learning.", "blue"),
        ("Dr. Ghulam Nabi", "ghulam.nabi@csas.pu.edu.pk", "GhulamN@2026", "SMTH-102", "Linear Algebra", "Vectors, matrices and linear systems.", "orange"),
        ("Ms. Fatima Khalid", "fatima.khalid@csas.pu.edu.pk", "FatimaK@2026", "GPST-201", "Pakistan Studies", "History, society and civic development of Pakistan.", "green"),
        ("Ms. Shaheen Ayyub", "shaheen@csas.pu.edu.pk", "Shaheen@2026", "HQ-201", "Understanding of Holy Quran (Fehm-e-Quran)", "Guided study and understanding of Quranic teachings.", "violet"),
    ]
    for name, email, password, code, title, description, color in teacher_specs:
        db.execute("INSERT OR IGNORE INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                   (name, email, generate_password_hash(password), "teacher"))
        teacher_id = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()[0]
        db.execute("INSERT OR IGNORE INTO courses(title,code,description,teacher_id,color) VALUES(?,?,?,?,?)",
                   (title, code, description, teacher_id, color))
        course_id = db.execute("SELECT id FROM courses WHERE code=?", (code,)).fetchone()[0]
        # Enrol the seeded demo student in the college subject spaces.
        student = db.execute("SELECT id FROM users WHERE email='student@learnspace.edu'").fetchone()
        if student:
            db.execute("INSERT OR IGNORE INTO enrollments(student_id,course_id) VALUES(?,?)", (student[0], course_id))
    # Keep only the seven CSAS semester courses requested for this project.
    allowed_codes = ("BSTA-201", "BSTA-202", "GENG-201", "GICT-201", "SMTH-102", "GPST-201", "HQ-201")
    placeholders = ",".join("?" for _ in allowed_codes)
    db.execute(f"DELETE FROM courses WHERE code NOT IN ({placeholders})", allowed_codes)
    # Three separate demo student accounts for the project team; safe to re-run.
    student_specs = [
        ("Ali Raza", "ali.raza@student.csas.pu.edu.pk", "AliRaza@2026"),
        ("Shaheer Raza Zaidi", "shaheer.zaidi@student.csas.pu.edu.pk", "Shaheer@2026"),
        ("Muhammad Ahmad", "muhammad.ahmad@student.csas.pu.edu.pk", "Ahmad@2026"),
    ]
    # All nine requested students are seeded idempotently and enrolled in every semester course.
    student_specs.extend([
        ("Sufiyan", "sufiyan@student.csas.pu.edu.pk", "Sufiyan@2026"),
        ("Ayesha", "ayesha@student.csas.pu.edu.pk", "Ayesha@2026"),
        ("Fiza", "fiza@student.csas.pu.edu.pk", "Fiza@2026"),
        ("Masroor", "masroor@student.csas.pu.edu.pk", "Masroor@2026"),
        ("Jannat", "jannat@student.csas.pu.edu.pk", "Jannat@2026"),
        ("Ahsan", "ahsan@student.csas.pu.edu.pk", "Ahsan@2026"),
    ])
    for name, email, password in student_specs:
        db.execute("INSERT OR IGNORE INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                   (name, email, generate_password_hash(password), "student"))
        sid = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()[0]
        for course in db.execute("SELECT id FROM courses").fetchall():
            db.execute("INSERT OR IGNORE INTO enrollments(student_id,course_id) VALUES(?,?)", (sid, course["id"]))
    # Official BS Biostatistics Semester III timetable (preserved from supplied image).
    timetable_rows = [
        ("GICT-201", "Monday", "08:15", "09:45", "B-102"),
        ("BSTA-201", "Monday", "09:45", "11:15", "Block-A / A-107"),
        ("GENG-201", "Monday", "11:15", "12:45", "B-102"),
        ("SMTH-102", "Monday", "13:15", "14:45", "A-107"),
        ("SMTH-102", "Tuesday", "08:15", "09:45", "A-107"),
        ("BSTA-202", "Tuesday", "09:45", "11:15", "A-107"),
        ("GPST-201", "Tuesday", "11:15", "13:15", "B-102"),
        ("HQ-201", "Tuesday", "13:15", "14:15", "B-102"),
        ("GENG-201", "Thursday", "08:15", "09:45", "B-102"),
        ("BSTA-201", "Thursday", "09:45", "11:15", "A-107"),
        ("BSTA-202", "Thursday", "11:45", "13:15", "A-107"),
        ("GICT-201", "Thursday", "13:15", "14:45", "B-102"),
    ]
    # Replace only the timetable demo rows with the supplied official schedule.
    db.execute("DELETE FROM timetable")
    for code, day, start, end, room in timetable_rows:
        cid = db.execute("SELECT id FROM courses WHERE code=?", (code,)).fetchone()
        if cid:
            db.execute("INSERT INTO timetable(course_id,day,start_time,end_time,room) VALUES(?,?,?,?,?)", (cid[0],day,start,end,room))
    db.commit()
    db.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") != role:
                flash("You do not have permission to open that page.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year, "today": date.today().isoformat()}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        selected_role = request.args.get("role", "")
        if user and check_password_hash(user["password_hash"], password) and (selected_role not in ("student", "teacher") or user["role"] == selected_role):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session["email"] = user["email"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password. Please try again.", "error")
    selected_role = request.args.get("role", "")
    if selected_role not in ("student", "teacher"):
        selected_role = ""
    return render_template("login.html", selected_role=selected_role)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user_id, role = session["user_id"], session["role"]
    announcements = db.execute("""SELECT a.*,u.name AS author FROM announcements a
        LEFT JOIN users u ON u.id=a.created_by
        WHERE a.audience='all' OR a.audience=? ORDER BY a.created_at DESC LIMIT 5""", (role,)).fetchall()
    if role == "student":
        # Repair any missing enrollments in existing demo databases so every student sees all seven semester courses.
        db.execute("INSERT OR IGNORE INTO enrollments(student_id, course_id) SELECT ?, id FROM courses", (user_id,))
        db.commit()
        courses = db.execute("""SELECT c.*,u.name AS teacher FROM courses c
            JOIN enrollments e ON e.course_id=c.id LEFT JOIN users u ON u.id=c.teacher_id
            WHERE e.student_id=? ORDER BY c.title""", (user_id,)).fetchall()
        assignments = db.execute("""SELECT a.*,c.title AS course_title,s.id AS submission_id,s.marks,s.feedback,s.file_name
            FROM assignments a JOIN courses c ON c.id=a.course_id
            JOIN enrollments e ON e.course_id=c.id
            LEFT JOIN submissions s ON s.assignment_id=a.id AND s.student_id=?
            WHERE e.student_id=? ORDER BY a.due_date ASC""", (user_id,user_id)).fetchall()
        grades = db.execute("""SELECT s.*,a.title AS assignment_title,a.total_marks,c.title AS course_title
            FROM submissions s JOIN assignments a ON a.id=s.assignment_id JOIN courses c ON c.id=a.course_id
            WHERE s.student_id=? AND s.marks IS NOT NULL ORDER BY s.graded_at DESC LIMIT 5""", (user_id,)).fetchall()
        total = len(assignments)
        pending = sum(1 for a in assignments if not a["submission_id"])
        completed = total - pending
        avg = db.execute("SELECT AVG(marks * 100.0 / a.total_marks) FROM submissions s JOIN assignments a ON a.id=s.assignment_id WHERE s.student_id=? AND marks IS NOT NULL", (user_id,)).fetchone()[0]
        att = db.execute("""SELECT COUNT(*) AS total, SUM(CASE WHEN status IN ('Present','Late') THEN 1 ELSE 0 END) AS attended
            FROM attendance WHERE student_id=?""", (user_id,)).fetchone()
        attendance_pct = round((att["attended"] or 0) * 100 / att["total"]) if att["total"] else 0
        return render_template("student_dashboard.html", courses=courses, assignments=assignments, grades=grades,
                               announcements=announcements, total=total, pending=pending, completed=completed,
                               average=round(avg or 0), attendance_pct=attendance_pct)
    courses = db.execute("SELECT c.*, COUNT(DISTINCT e.student_id) AS student_count FROM courses c LEFT JOIN enrollments e ON e.course_id=c.id WHERE c.teacher_id=? GROUP BY c.id ORDER BY c.title", (user_id,)).fetchall()
    assignment_count = db.execute("SELECT COUNT(*) FROM assignments WHERE created_by=?", (user_id,)).fetchone()[0]
    pending_reviews = db.execute("""SELECT COUNT(*) FROM submissions s JOIN assignments a ON a.id=s.assignment_id
        WHERE a.created_by=? AND s.marks IS NULL""", (user_id,)).fetchone()[0]
    students = db.execute("SELECT COUNT(DISTINCT e.student_id) FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE c.teacher_id=?", (user_id,)).fetchone()[0]
    return render_template("teacher_dashboard.html", courses=courses, assignment_count=assignment_count,
                           pending_reviews=pending_reviews, students=students, announcements=announcements)

@app.route("/courses")
@login_required
def courses():
    db = get_db()
    if session["role"] == "student":
        # Keep existing student accounts in sync with all available semester courses.
        db.execute("INSERT OR IGNORE INTO enrollments(student_id, course_id) SELECT ?, id FROM courses", (session["user_id"],))
        db.commit()
        items = db.execute("""SELECT c.*,u.name AS teacher FROM courses c JOIN enrollments e ON e.course_id=c.id
            LEFT JOIN users u ON u.id=c.teacher_id WHERE e.student_id=? ORDER BY c.title""", (session["user_id"],)).fetchall()
    else:
        items = db.execute("""SELECT c.*,u.name AS teacher,COUNT(DISTINCT e.student_id) AS student_count
            FROM courses c LEFT JOIN users u ON u.id=c.teacher_id LEFT JOIN enrollments e ON e.course_id=c.id
            WHERE c.teacher_id=? GROUP BY c.id ORDER BY c.title""", (session["user_id"],)).fetchall()
    return render_template("courses.html", courses=items)

@app.route("/assignments")
@login_required
def assignments():
    db = get_db()
    if session["role"] == "student":
        items = db.execute("""SELECT a.*,c.title AS course_title,s.id AS submission_id,s.text_answer,s.file_name,s.marks,s.feedback,s.submitted_at
            FROM assignments a JOIN courses c ON c.id=a.course_id JOIN enrollments e ON e.course_id=c.id
            LEFT JOIN submissions s ON s.assignment_id=a.id AND s.student_id=?
            WHERE e.student_id=? ORDER BY a.due_date""", (session["user_id"],session["user_id"])).fetchall()
    else:
        items = db.execute("""SELECT a.*,c.title AS course_title,
            (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id=a.id) AS submissions_count,
            (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id=a.id AND s.marks IS NULL) AS ungraded_count
            FROM assignments a JOIN courses c ON c.id=a.course_id
            WHERE c.teacher_id=? ORDER BY a.due_date""", (session["user_id"],)).fetchall()
    course_options = db.execute("SELECT id,title FROM courses WHERE teacher_id=? ORDER BY title", (session["user_id"],)).fetchall() if session["role"] == "teacher" else []
    return render_template("assignments.html", assignments=items, course_options=course_options)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/assignments/create", methods=["POST"])
@role_required("teacher")
def create_assignment():
    db = get_db()
    course_id = request.form.get("course_id", type=int)
    course = db.execute("SELECT id FROM courses WHERE id=? AND teacher_id=?", (course_id,session["user_id"])).fetchone()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("due_date", "")
    total_marks = request.form.get("total_marks", type=int)
    if not course or not title or not description or not due_date or not total_marks or total_marks < 1:
        flash("Please complete all fields correctly.", "error")
    else:
        db.execute("INSERT INTO assignments(course_id,title,description,due_date,total_marks,created_by) VALUES(?,?,?,?,?,?)",
                   (course_id,title,description,due_date,total_marks,session["user_id"]))
        db.commit()
        flash("Assignment published successfully.", "success")
    return redirect(url_for("assignments"))

@app.route("/assignments/<int:assignment_id>/delete", methods=["POST"])
@role_required("teacher")
def delete_assignment(assignment_id):
    db = get_db()
    assignment = db.execute("""SELECT a.id FROM assignments a JOIN courses c ON c.id=a.course_id
        WHERE a.id=? AND c.teacher_id=?""", (assignment_id, session["user_id"])).fetchone()
    if not assignment:
        flash("Assignment not found in your assigned subjects.", "error")
    else:
        db.execute("DELETE FROM assignments WHERE id=?", (assignment_id,))
        db.commit()
        flash("Assignment and its submissions were deleted.", "success")
    return redirect(url_for("assignments"))

@app.route("/assignments/<int:assignment_id>/submit", methods=["POST"])
@role_required("student")
def submit_assignment(assignment_id):
    db = get_db()
    assignment = db.execute("""SELECT a.* FROM assignments a JOIN enrollments e ON e.course_id=a.course_id
        WHERE a.id=? AND e.student_id=?""", (assignment_id,session["user_id"])).fetchone()
    if not assignment:
        flash("Assignment not found in your courses.", "error")
        return redirect(url_for("assignments"))
    text_answer = request.form.get("text_answer", "").strip()
    upload = request.files.get("attachment")
    file_name = ""
    if upload and upload.filename:
        safe_name = secure_filename(upload.filename)
        if not allowed_file(safe_name):
            flash("Unsupported file type. Use PDF, DOCX, PPTX, TXT, image or ZIP.", "error")
            return redirect(url_for("assignments"))
        stored_name = f"{session['user_id']}_{assignment_id}_{int(datetime.now().timestamp())}_{safe_name}"
        upload.save(os.path.join(UPLOAD_DIR, stored_name))
        file_name = stored_name
    if not text_answer and not file_name:
        flash("Write an answer or attach a file before submitting.", "error")
        return redirect(url_for("assignments"))
    db.execute("""INSERT INTO submissions(assignment_id,student_id,text_answer,file_name,submitted_at,marks,feedback,graded_by,graded_at)
        VALUES(?,?,?,?,CURRENT_TIMESTAMP,NULL,'',NULL,NULL)
        ON CONFLICT(assignment_id,student_id) DO UPDATE SET
        text_answer=excluded.text_answer,file_name=CASE WHEN excluded.file_name='' THEN submissions.file_name ELSE excluded.file_name END,
        submitted_at=CURRENT_TIMESTAMP,marks=NULL,feedback='',graded_by=NULL,graded_at=NULL""",
        (assignment_id,session["user_id"],text_answer,file_name))
    db.commit()
    flash("Assignment submitted successfully.", "success")
    return redirect(url_for("assignments"))

@app.route("/submissions")
@role_required("teacher")
def submissions():
    items = get_db().execute("""SELECT s.*,u.name AS student_name,u.email AS student_email,
        a.title AS assignment_title,a.total_marks,a.due_date,c.title AS course_title
        FROM submissions s JOIN users u ON u.id=s.student_id
        JOIN assignments a ON a.id=s.assignment_id JOIN courses c ON c.id=a.course_id
        WHERE c.teacher_id=? ORDER BY (s.marks IS NULL) DESC,s.submitted_at DESC""", (session["user_id"],)).fetchall()
    return render_template("submissions.html", submissions=items)

@app.route("/submissions/<int:submission_id>/grade", methods=["POST"])
@role_required("teacher")
def grade_submission(submission_id):
    db = get_db()
    sub = db.execute("""SELECT s.id,a.total_marks FROM submissions s JOIN assignments a ON a.id=s.assignment_id
        JOIN courses c ON c.id=a.course_id WHERE s.id=? AND c.teacher_id=?""",
        (submission_id,session["user_id"])).fetchone()
    marks = request.form.get("marks", type=float)
    feedback = request.form.get("feedback", "").strip()
    if not sub or marks is None or marks < 0 or marks > sub["total_marks"]:
        flash("Marks must be between 0 and the assignment's total marks.", "error")
    else:
        db.execute("UPDATE submissions SET marks=?,feedback=?,graded_by=?,graded_at=CURRENT_TIMESTAMP WHERE id=?",
                   (marks,feedback,session["user_id"],submission_id))
        db.commit()
        flash("Grade saved successfully.", "success")
    return redirect(url_for("submissions"))

@app.route("/resources", methods=["GET","POST"])
@login_required
def resources():
    db = get_db()
    if request.method == "POST":
        if session["role"] != "teacher":
            flash("Only teachers can add resources.", "error")
            return redirect(url_for("resources"))
        course_id = request.form.get("course_id", type=int)
        course = db.execute("SELECT id FROM courses WHERE id=? AND teacher_id=?", (course_id,session["user_id"])).fetchone()
        title = request.form.get("title","").strip()
        description = request.form.get("description","").strip()
        url = request.form.get("url","").strip()
        upload = request.files.get("attachment")
        file_name = ""
        if upload and upload.filename:
            safe_name = secure_filename(upload.filename)
            if not allowed_file(safe_name):
                flash("Unsupported file type.", "error")
                return redirect(url_for("resources"))
            file_name = f"resource_{session['user_id']}_{int(datetime.now().timestamp())}_{safe_name}"
            upload.save(os.path.join(UPLOAD_DIR,file_name))
        if course and title and (url or file_name):
            db.execute("INSERT INTO resources(course_id,title,description,file_name,url,uploaded_by) VALUES(?,?,?,?,?,?)",
                       (course_id,title,description,file_name,url,session["user_id"]))
            db.commit()
            flash("Resource added successfully.", "success")
        else:
            flash("Select a course, enter a title, and provide a URL or file.", "error")
        return redirect(url_for("resources"))
    if session["role"] == "student":
        items = db.execute("""SELECT r.*,c.title AS course_title FROM resources r JOIN courses c ON c.id=r.course_id
            JOIN enrollments e ON e.course_id=c.id WHERE e.student_id=? ORDER BY r.created_at DESC""", (session["user_id"],)).fetchall()
        course_options = []
    else:
        items = db.execute("""SELECT r.*,c.title AS course_title FROM resources r JOIN courses c ON c.id=r.course_id
            WHERE c.teacher_id=? ORDER BY r.created_at DESC""", (session["user_id"],)).fetchall()
        course_options = db.execute("SELECT id,title FROM courses WHERE teacher_id=? ORDER BY title", (session["user_id"],)).fetchall()
    return render_template("resources.html", resources=items, courses=course_options)

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    safe = os.path.basename(filename)
    db = get_db()
    if session["role"] == "teacher":
        row = db.execute("""SELECT 1 FROM submissions s JOIN assignments a ON a.id=s.assignment_id JOIN courses c ON c.id=a.course_id
            WHERE s.file_name=? AND c.teacher_id=? UNION SELECT 1 FROM resources r JOIN courses c ON c.id=r.course_id
            WHERE r.file_name=? AND c.teacher_id=? LIMIT 1""",
            (safe,session["user_id"],safe,session["user_id"])).fetchone()
    else:
        row = db.execute("""SELECT 1 FROM submissions WHERE file_name=? AND student_id=?
            UNION SELECT 1 FROM resources r JOIN enrollments e ON e.course_id=r.course_id
            WHERE r.file_name=? AND e.student_id=? LIMIT 1""",
            (safe,session["user_id"],safe,session["user_id"])).fetchone()
    if not row:
        flash("You do not have access to this file.", "error")
        return redirect(url_for("dashboard"))
    return send_from_directory(UPLOAD_DIR, safe, as_attachment=True)

@app.route("/grades")
@role_required("student")
def grades():
    items = get_db().execute("""SELECT s.*,a.title AS assignment_title,a.total_marks,a.due_date,c.title AS course_title,
        u.name AS teacher_name FROM submissions s JOIN assignments a ON a.id=s.assignment_id
        JOIN courses c ON c.id=a.course_id LEFT JOIN users u ON u.id=a.created_by
        WHERE s.student_id=? ORDER BY s.submitted_at DESC""", (session["user_id"],)).fetchall()
    return render_template("grades.html", submissions=items)

@app.route("/announcements", methods=["GET","POST"])
@login_required
def announcements():
    db = get_db()
    if request.method == "POST":
        if session["role"] != "teacher":
            flash("Only teachers can publish announcements.", "error")
            return redirect(url_for("announcements"))
        title = request.form.get("title","").strip()
        message = request.form.get("message","").strip()
        audience = request.form.get("audience","all")
        if audience not in ("all","student","teacher"):
            audience = "all"
        if title and message:
            db.execute("INSERT INTO announcements(title,message,audience,created_by) VALUES(?,?,?,?)",
                       (title,message,audience,session["user_id"]))
            db.commit()
            flash("Announcement published.", "success")
        else:
            flash("Enter both a title and message.", "error")
        return redirect(url_for("announcements"))
    items = db.execute("""SELECT a.*,u.name AS author FROM announcements a LEFT JOIN users u ON u.id=a.created_by
        WHERE a.audience='all' OR a.audience=? ORDER BY a.created_at DESC""", (session["role"],)).fetchall()
    return render_template("announcements.html", announcements=items)

@app.route("/timetable")
@login_required
def timetable():
    db = get_db()
    if session["role"] == "student":
        items = db.execute("""SELECT t.*,c.title AS course_title,c.code,u.name AS teacher_name FROM timetable t
            JOIN courses c ON c.id=t.course_id JOIN enrollments e ON e.course_id=c.id
            LEFT JOIN users u ON u.id=c.teacher_id WHERE e.student_id=?
            ORDER BY CASE t.day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END,t.start_time""", (session["user_id"],)).fetchall()
    else:
        items = db.execute("""SELECT t.*,c.title AS course_title,c.code,u.name AS teacher_name FROM timetable t
            JOIN courses c ON c.id=t.course_id LEFT JOIN users u ON u.id=c.teacher_id
            WHERE c.teacher_id=? ORDER BY CASE t.day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END,t.start_time""", (session["user_id"],)).fetchall()
    return render_template("timetable.html", entries=items)

@app.route("/notifications")
@login_required
def notifications():
    db = get_db()
    role, uid = session["role"], session["user_id"]
    today = date.today()
    reminders = []
    if role == "student":
        rows = db.execute("""SELECT a.title,a.due_date,c.title AS course_title,c.code,s.id AS submission_id
            FROM assignments a JOIN courses c ON c.id=a.course_id JOIN enrollments e ON e.course_id=c.id
            LEFT JOIN submissions s ON s.assignment_id=a.id AND s.student_id=? WHERE e.student_id=? ORDER BY a.due_date""", (uid,uid)).fetchall()
    else:
        rows = db.execute("""SELECT a.title,a.due_date,c.title AS course_title,c.code,NULL AS submission_id
            FROM assignments a JOIN courses c ON c.id=a.course_id WHERE c.teacher_id=? ORDER BY a.due_date""", (uid,)).fetchall()
    for row in rows:
        try:
            due = date.fromisoformat(row["due_date"][:10])
        except (ValueError, TypeError):
            continue
        days = (due - today).days
        if -30 <= days <= 3:
            if role == "student" and row["submission_id"]:
                continue
            if days < 0:
                label, tone = f"Overdue by {abs(days)} day(s)", "overdue"
            elif days == 0:
                label, tone = "Due today", "urgent"
            elif days == 1:
                label, tone = "Due tomorrow", "urgent"
            else:
                label, tone = f"Due in {days} days", "soon"
            reminders.append({"title": row["title"], "course": row["course_title"], "date": row["due_date"], "message": label, "tone": tone, "kind": "Assignment deadline"})
    ann = db.execute("""SELECT a.title,a.message,a.created_at,c.title AS course_title FROM announcements a
        LEFT JOIN users u ON u.id=a.created_by LEFT JOIN courses c ON c.teacher_id=u.id
        WHERE a.audience IN ('all',?) ORDER BY a.created_at DESC LIMIT 30""", (role,)).fetchall()
    for a in ann:
        reminders.append({"title": a["title"], "course": a["course_title"] or "All courses", "date": a["created_at"][:10], "message": a["message"], "tone": "notice", "kind": "Announcement"})
    reminders.sort(key=lambda x: (0 if x["tone"] in ("overdue","urgent") else 1, x["date"]))
    return render_template("notifications.html", notifications=reminders)

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    db = get_db()
    if request.method == "POST":
        if session.get("role") != "teacher":
            flash("Only teachers can mark attendance.", "error")
            return redirect(url_for("attendance"))
        course_id = request.form.get("course_id", type=int)
        day = request.form.get("attendance_date", date.today().isoformat())
        course = db.execute("SELECT id FROM courses WHERE id=? AND teacher_id=?", (course_id, session["user_id"])).fetchone()
        if not course:
            flash("Please select one of your assigned subjects.", "error")
            return redirect(url_for("attendance"))
        students = db.execute("SELECT u.id FROM users u JOIN enrollments e ON e.student_id=u.id WHERE e.course_id=? AND u.role='student'", (course_id,)).fetchall()
        for student in students:
            status = request.form.get(f"status_{student['id']}", "Absent")
            if status not in ("Present", "Absent", "Late"):
                status = "Absent"
            db.execute("INSERT INTO attendance(course_id,student_id,attendance_date,status,marked_by) VALUES(?,?,?,?,?) ON CONFLICT(course_id,student_id,attendance_date) DO UPDATE SET status=excluded.status,marked_by=excluded.marked_by,marked_at=CURRENT_TIMESTAMP",
                       (course_id, student["id"], day, status, session["user_id"]))
        db.commit()
        flash("Attendance saved successfully.", "success")
        return redirect(url_for("attendance", course_id=course_id, day=day))
    if session.get("role") == "teacher":
        courses = db.execute("SELECT id,title,code FROM courses WHERE teacher_id=? ORDER BY title", (session["user_id"],)).fetchall()
        selected_id = request.args.get("course_id", type=int) or (courses[0]["id"] if courses else None)
        selected_day = request.args.get("day", date.today().isoformat())
        roster = db.execute("SELECT u.id,u.name,u.email,at.status FROM users u JOIN enrollments e ON e.student_id=u.id LEFT JOIN attendance at ON at.student_id=u.id AND at.course_id=e.course_id AND at.attendance_date=? WHERE e.course_id=? AND u.role='student' ORDER BY u.name", (selected_day, selected_id)).fetchall() if selected_id else []
        history = db.execute("SELECT at.attendance_date,at.status,u.name AS student_name,c.title AS course_title FROM attendance at JOIN users u ON u.id=at.student_id JOIN courses c ON c.id=at.course_id WHERE c.teacher_id=? ORDER BY at.attendance_date DESC, u.name LIMIT 30", (session["user_id"],)).fetchall()
        return render_template("attendance.html", courses=courses, selected_id=selected_id, selected_day=selected_day, roster=roster, history=history)
    rows = db.execute("SELECT c.title,c.code,COUNT(at.id) AS marked,SUM(CASE WHEN at.status='Present' THEN 1 ELSE 0 END) AS present,SUM(CASE WHEN at.status='Late' THEN 1 ELSE 0 END) AS late,SUM(CASE WHEN at.status='Absent' THEN 1 ELSE 0 END) AS absent FROM courses c JOIN enrollments e ON e.course_id=c.id AND e.student_id=? LEFT JOIN attendance at ON at.course_id=c.id AND at.student_id=e.student_id WHERE c.id IN (SELECT course_id FROM enrollments WHERE student_id=?) GROUP BY c.id ORDER BY c.title", (session["user_id"],session["user_id"])).fetchall()
    total_marked = sum(r["marked"] or 0 for r in rows)
    total_present = sum(r["present"] or 0 for r in rows)
    percent = round(total_present * 100 / total_marked) if total_marked else 0
    return render_template("attendance.html", rows=rows, attendance_percent=percent)

@app.route("/reports")
@role_required("teacher")
def reports():
    db = get_db()
    courses = db.execute("""SELECT c.id,c.title,c.code,COUNT(DISTINCT e.student_id) AS students,
        COUNT(DISTINCT a.id) AS assignments,COUNT(s.id) AS submissions,
        ROUND(AVG(CASE WHEN s.marks IS NOT NULL THEN s.marks*100.0/a.total_marks END),1) AS average
        FROM courses c LEFT JOIN enrollments e ON e.course_id=c.id
        LEFT JOIN assignments a ON a.course_id=c.id LEFT JOIN submissions s ON s.assignment_id=a.id
        WHERE c.teacher_id=? GROUP BY c.id ORDER BY c.title""", (session["user_id"],)).fetchall()
    return render_template("reports.html", courses=courses)

@app.errorhandler(413)
def file_too_large(_error):
    flash("File is too large. Maximum upload size is 8 MB.", "error")
    return redirect(request.referrer or url_for("dashboard"))

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you are looking for could not be found."), 404

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
