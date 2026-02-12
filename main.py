from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
#CORS(app, supports_credentials=True, origins=["http://localhost:9002"])
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True,origins=["http://localhost:9002"])


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
        "SELECT * FROM users WHERE email=%s AND password_hash=%s",
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
    room_id = data["room_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert into users
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
        (name, email, password, "student")
    )

    user_id = cursor.lastrowid

    # Insert into students with room_id
    cursor.execute(
        "INSERT INTO students (user_id, rollNo, dept, year, phone, room_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, rollNo, dept, year, phone, room_id)
    )

    # Increase room occupancy
    cursor.execute(
        "UPDATE rooms SET occupied = occupied + 1 WHERE id = %s",
        (room_id,)
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
    s.phone,
    r.roomNo
FROM users u
JOIN students s ON u.id = s.user_id
LEFT JOIN rooms r ON s.room_id = r.id
WHERE u.role = 'student'
"""



    cursor.execute(query)
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(students)


@app.route("/api/admin/available-rooms", methods=["GET"])
def get_available_rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, roomNo, capacity, occupied
        FROM rooms
        WHERE occupied < capacity
    """)

    rooms = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(rooms), 200


@app.route("/api/admin/rooms", methods=["GET"])
def get_rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, roomNo, capacity, occupied
        FROM rooms
    """)
    rooms = cursor.fetchall()

    # Get students per room
    for room in rooms:
        cursor.execute("""
            SELECT u.id, u.name
            FROM students s
            JOIN users u ON u.id = s.user_id
            WHERE s.room_id = %s
        """, (room["id"],))
        room["students"] = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(rooms), 200


@app.route("/api/admin/allocate", methods=["POST"])
def allocate_student():
    data = request.get_json()
    student_id = data["student_id"]
    room_id = data["room_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # assign room
    cursor.execute("""
        UPDATE students SET room_id = %s WHERE user_id = %s
    """, (room_id, student_id))

    # increase occupied
    cursor.execute("""
        UPDATE rooms SET occupied = occupied + 1 WHERE id = %s
    """, (room_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Student allocated"}), 200


@app.route("/api/admin/rooms", methods=["POST"])
def add_room():
    data = request.get_json()

    roomNo = data["roomNo"]
    capacity = data["capacity"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO rooms (roomNo, capacity, occupied)
        VALUES (%s, %s, 0)
    """, (roomNo, capacity))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Room added"}), 201


@app.route("/api/admin/unassigned-students", methods=["GET"])
def get_unassigned_students():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.id, u.name
        FROM users u
        JOIN students s ON u.id = s.user_id
        WHERE s.room_id IS NULL
    """)

    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(students)



@app.route("/api/admin/allocate", methods=["POST"])
def allocate():
    data = request.get_json()
    student_id = data["student_id"]
    room_id = data["room_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE students SET room_id=%s WHERE user_id=%s",
        (room_id, student_id)
    )

    cursor.execute(
        "UPDATE rooms SET occupied = occupied + 1 WHERE id=%s",
        (room_id,)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Allocated"})


@app.route("/api/admin/fees", methods=["GET"])
def get_fees():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
        f.id,
        f.studentId,
        u.name,
        f.amount,
        f.due_date,
        f.status
    FROM fees f
    JOIN users u ON f.studentId = u.id
""")


    fees = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(fees)




@app.route("/api/admin/complaints", methods=["GET"])
def get_complaints():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="hostel_db"
    )

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            c.id,
            c.title,
            c.description,
            c.status,
            c.created_at,
            u.name AS studentName
        FROM complaints c
        JOIN users u ON c.student_id = u.id
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(rows)


@app.route("/api/admin/complaints/<int:complaint_id>", methods=["PUT"])
def update_complaint_status(complaint_id):
    data = request.get_json()
    status = data.get("status")

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="hostel_db"
    )

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE complaints
        SET status = %s
        WHERE id = %s
    """, (status, complaint_id))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Status updated"})

@app.route("/api/admin/notices", methods=["GET"])
def get_notices():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="hostel_db"
    )
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, content, summary, created_at
        FROM notices
        ORDER BY created_at DESC
    """)

    notices = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(notices)



@app.route("/api/admin/notices", methods=["POST"])
def create_notice():
    data = request.get_json()

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="hostel_db"
    )
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO notices (title, content, summary)
        VALUES (%s, %s, %s)
    """, (
        data.get("title"),
        data.get("content"),
        data.get("summary")
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Notice created successfully"})



@app.route("/api/student/me", methods=["GET"])
def student_me():
    from flask import session, jsonify

    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["user_id"]
    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    # Fetch student basic info
    cursor.execute("""
        SELECT u.id, u.name, u.email, sp.room_id
        FROM users u
        JOIN student_profiles sp ON sp.user_id = u.id
        WHERE u.id = %s AND u.role = 'student'
    """, (user_id,))
    
    student = cursor.fetchone()

    if not student:
        return jsonify({"error": "Student not found"}), 404

    # Fetch room number (if allocated)
    roomNo = None
    if student["room_id"]:
        cursor.execute("SELECT roomNo FROM rooms WHERE id = %s", (student["room_id"],))
        room = cursor.fetchone()
        if room:
            roomNo = room["roomNo"]

    # Fetch fee info
    cursor.execute("""
        SELECT amount, status, due_date
        FROM fees
        WHERE studentId = %s
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))
    
    fee = cursor.fetchone()

    cursor.close()
    conn.close()
    return jsonify({
        "id": student["id"],
        "name": student["name"],
        "email": student["email"],
        "roomNo": roomNo,
        "fee": fee
    })

@app.route("/api/student/<int:user_id>")
def get_student_dashboard(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.id, u.name, u.email,
               r.roomNo,
               f.amount,
               f.status AS feeStatus
        FROM users u
        LEFT JOIN students s ON u.id = s.user_id
        LEFT JOIN rooms r ON s.room_id = r.id
        LEFT JOIN fees f ON f.studentId = u.id
        WHERE u.id = %s
    """, (user_id,))

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(student)


@app.route("/api/student/fees", methods=["GET"])
def student_get_own_fees():

    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"message": "User ID required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, amount, due_date, status
        FROM fees
        WHERE studentId = %s
        ORDER BY due_date DESC
    """, (user_id,))

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(data), 200


@app.route("/api/student/payments/<int:user_id>")
def get_student_payment_history(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, amount, payment_date
        FROM payments
        WHERE studentId = %s
        ORDER BY payment_date DESC
    """, (user_id,))

    payments = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(payments), 200


@app.route("/api/student/my-complaints/<int:user_id>", methods=["GET"])
def student_get_my_complaints(user_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, title, description, status, created_at AS date
        FROM complaints
        WHERE student_id = %s
        ORDER BY created_at DESC
    """, (user_id,))

    complaints = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(complaints), 200

@app.route("/api/student/my-complaints", methods=["POST", "OPTIONS"])
def student_create_complaint():

    if request.method == "OPTIONS":
        return '', 200

    data = request.json
    student_id = data.get("student_id")
    title = data.get("title")
    description = data.get("description")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO complaints (student_id, title, description, status, created_at)
        VALUES (%s, %s, %s, 'pending', NOW())
    """, (student_id, title, description))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Complaint submitted"}), 201



# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(debug=True)
