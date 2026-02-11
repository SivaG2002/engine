from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://localhost:9002"])

# ---------------- DB CONFIG ----------------

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "hostel_db"
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# ---------------- LOGIN ----------------

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, password)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return jsonify({"message": "Invalid credentials"}), 401

    return jsonify({
        "message": "Login successful",
        "role": user["role"],
        "user_id": user["id"]
    }), 200


# ---------------- GET ALL STUDENTS ----------------


# ---------------- CREATE STUDENT ----------------

@app.route("/api/admin/students", methods=["POST"])
def create_student():
    data = request.get_json()

    name = data["name"]
    email = data["email"]
    password = data["password"]
    rollNo = data["rollNo"]
    dept = data["dept"]
    year = data["year"]
    phone = data["phone"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # INSERT INTO users table (USE password_hash column)
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
        (name, email, password, "student")
    )

    user_id = cursor.lastrowid

    # INSERT INTO students table
    cursor.execute(
        "INSERT INTO students (user_id, rollNo, dept, year, phone) VALUES (%s, %s, %s, %s, %s)",
        (user_id, rollNo, dept, year, phone)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Student created"}), 201


# ---------------- ADMIN SUMMARY ----------------

@app.route("/api/admin/summary", methods=["GET"])
def admin_summary():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total_students FROM users WHERE role='student'")
    total_students = cursor.fetchone()["total_students"]

    cursor.execute("SELECT COUNT(*) as total_rooms FROM rooms")
    total_rooms = cursor.fetchone()["total_rooms"]

    cursor.execute("SELECT COUNT(*) as occupied_rooms FROM rooms WHERE occupied > 0")
    occupied_rooms = cursor.fetchone()["occupied_rooms"]

    cursor.execute("SELECT COUNT(*) as pending_complaints FROM complaints WHERE status='pending'")
    pending_complaints = cursor.fetchone()["pending_complaints"]

    cursor.close()
    conn.close()

    return jsonify({
        "total_students": total_students,
        "total_rooms": total_rooms,
        "occupied_rooms": occupied_rooms,
        "pending_complaints": pending_complaints
    }), 200




@app.route("/api/student/complaints", methods=["POST"])
def submit_complaint():

    data = request.json

    student_id = data.get("student_id")
    title = data.get("title")
    description = data.get("description")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO complaints (student_id, title, description, status, date) VALUES (%s, %s, %s, %s, CURDATE())",
        (student_id, title, description, "pending")
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Complaint submitted"}), 201


@app.route("/api/student/complaints/<int:user_id>", methods=["GET"])
def get_student_complaints(user_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT id, title, description, status, date
    FROM complaints
    WHERE student_id = %s
    """

    cursor.execute(query, (user_id,))
    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(complaints), 200


@app.route("/api/student/fees/<int:user_id>", methods=["GET"])
def get_student_fees(user_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT id, amount, due_date, status
    FROM fees
    WHERE student_id = %s
    """

    cursor.execute(query, (user_id,))
    fees = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(fees), 200




@app.route("/api/admin/dashboard", methods=["GET"])
def admin_dashboard():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # total students
    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='student'")
    total_students = cursor.fetchone()["total"]

    # available rooms
    cursor.execute("""
        SELECT COUNT(*) AS available
        FROM rooms
        WHERE occupied < capacity
    """)
    available_rooms = cursor.fetchone()["available"]

    # active complaints
    cursor.execute("""
        SELECT COUNT(*) AS pending
        FROM complaints
        WHERE status='Pending' OR status='In Progress'
    """)
    pending_complaints = cursor.fetchone()["pending"]

    cursor.close()
    conn.close()

    return jsonify({
        "total_students": total_students,
        "available_rooms": available_rooms,
        "pending_complaints": pending_complaints
    })


@app.route("/api/admin/students", methods=["GET"])
def get_students():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
SELECT 
    u.id,
    u.name,
    u.email,
    s.rollNo,
    s.dept,
    s.year,
    s.phone
FROM users u
JOIN students s ON u.id = s.user_id
WHERE u.role = 'student'
"""


    cursor.execute(query)
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(students)


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(debug=True)
