import json
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'hostel-secret-2025'

DB_FILE = 'data/db.json'

def load_db():
    if not os.path.exists(DB_FILE):
        initial = {
            "users": [{"id": 1, "username": "warden1", "password": "warden123", "role": "warden", "name": "Mr. Rajesh"}],
            "matrons": [{"id": 1, "name": "Mrs. Sunita", "username": "matron1", "password": "matron123", "contact": "9876543210"}],
            "students": [],
            "rooms": [{"room_no": f"{100+i}", "capacity": 4, "occupied": 0, "students": []} for i in range(1, 26)],
            "applications": [],
            "payments": [],
            "complaints": [],
            "vacate_requests": []
        }
        os.makedirs('data', exist_ok=True)
        with open(DB_FILE, 'w') as f:
            json.dump(initial, f, indent=2)
        return initial
    else:
        with open(DB_FILE, 'r') as f:
            db = json.load(f)
        for key in ["users","matrons","students","rooms","applications","payments","complaints","vacate_requests"]:
            if key not in db:
                db[key] = []
        for room in db['rooms']:
            if 'students' not in room:
                room['students'] = []
        return db

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

DB = load_db()

def role_required(role):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'role' not in session or session['role'] != role:
                flash("Access denied!", "danger")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# === HOME ===
@app.route('/')
def home():
    return render_template('index.html')

# === LOGIN ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        user = next((u for u in DB.get('users', []) if u['username'] == username and u['password'] == password), None)
        if user:
            session.update({'user_id': user['id'], 'username': user['username'], 'role': user['role'], 'name': user.get('name', user['username'])})
            return redirect(url_for('warden_dashboard'))

        matron = next((m for m in DB.get('matrons', []) if m['username'] == username and m.get('password') == password), None)
        if matron:
            session.update({'user_id': matron['id'], 'username': matron['username'], 'role': 'matron', 'name': matron['name']})
            return redirect(url_for('matron_dashboard'))

        student = next((s for s in DB.get('students', []) if s['email'] == username and s['password'] == password), None)
        if student:
            session.update({'user_id': student['id'], 'username': student['email'], 'role': 'student', 'name': student['name']})
            if student.get('room'):
                return redirect(url_for('student_home'))
            else:
                return redirect(url_for('student_dashboard'))

        flash("Invalid credentials!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('home'))

# === STUDENT REGISTRATION ===
@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email'].lower()
        password = request.form['password']

        if any(s.get('email') == email for s in DB['students']):
            flash("Email already registered!", "danger")
            return redirect(url_for('student_register'))

        new_id = max([s['id'] for s in DB['students']], default=0) + 1
        DB['students'].append({
            "id": new_id,
            "name": name,
            "email": email,
            "password": password,
            "room": None,
            "has_applied": False
        })
        save_db(DB)

        session.update({'user_id': new_id, 'username': email, 'role': 'student', 'name': name})
        return redirect(url_for('student_dashboard'))

    return render_template('student/register.html')

# === STUDENT DASHBOARD (FORM) ===
@app.route('/student/dashboard')
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    student = next(s for s in DB['students'] if s['id'] == session['user_id'])
    has_applied = student.get('has_applied', False)

    return render_template('student/dashboard.html', student=student, has_applied=has_applied)

# === SUBMIT APPLICATION ===
@app.route('/student/submit_application', methods=['POST'])
@role_required('student')
def submit_room_application():
    student = next(s for s in DB['students'] if s['id'] == session['user_id'])

    application = {
        "student_id": student['id'],
        "name": student['name'],
        "email": student['email'],
        "address": request.form['address'],
        "department": request.form['department'],
        "student_contact": request.form['student_contact'],
        "class": request.form['class'],
        "guardian_name": request.form['guardian_name'],
        "guardian_details": request.form['guardian_details'],
        "guardian_contact": request.form['guardian_contact'],
        "status": "Pending",
        "applied_on": datetime.now().strftime("%d-%m-%Y")
    }

    DB['applications'].append(application)
    student['has_applied'] = True
    save_db(DB)
    flash("Your application is submitted successfully and please wait for the approval", "success")
    return redirect(url_for('student_dashboard'))

# === STUDENT HOME (AFTER ROOM APPROVAL) ===
@app.route('/student/home')
def student_home():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    student = next(s for s in DB['students'] if s['id'] == session['user_id'])
    
    if not student.get('room'):
        flash("Your room is not allocated yet.", "info")
        return redirect(url_for('student_dashboard'))

    current_month = datetime.now().strftime("%B %Y")
    paid_this_month = any(
        p['student_id'] == student['id'] and 
        p['month_year'] == current_month and 
        p['status'] == 'Paid' 
        for p in DB.get('payments', [])
    )

    return render_template('student/home.html', 
                         student=student, 
                         current_month=current_month,
                         rent_paid=paid_this_month)

# === PAY RENT ===
@app.route('/student/pay_rent', methods=['GET', 'POST'])
@role_required('student')
def pay_rent():
    student = next(s for s in DB['students'] if s['id'] == session['user_id'])
    
    if not student.get('room'):
        flash("No room allocated!", "danger")
        return redirect(url_for('student_home'))

    current_month = datetime.now().strftime("%B %Y")
    
    if 'payments' not in DB:
        DB['payments'] = []

    already_paid = any(p['student_id'] == student['id'] and p['month_year'] == current_month for p in DB['payments'])

    if already_paid:
        flash(f"Rent already paid for {current_month}!", "info")
        return redirect(url_for('student_home'))

    if request.method == 'POST':
        DB['payments'].append({
            "student_id": student['id'],
            "name": student['name'],
            "room_no": student['room'],
            "month_year": current_month,
            "amount": 500,
            "status": "Paid",
            "paid_on": datetime.now().strftime("%d-%m-%Y")
        })
        save_db(DB)
        flash(f"500 rent paid successfully for {current_month}!", "success")
        return redirect(url_for('student_home'))

    return render_template('student/pay_rent.html', student=student, current_month=current_month)

# === PAYMENT HISTORY ===
@app.route('/student/payment_history')
@role_required('student')
def payment_history():
    student = next(s for s in DB['students'] if s['id'] == session['user_id'])
    payments = [p for p in DB.get('payments', []) if p['student_id'] == student['id']]
    return render_template('student/payment_history.html', payments=payments, student=student)

# === ADD COMPLAINT ===
@app.route('/student/add_complaint', methods=['GET', 'POST'])
@role_required('student')
def add_complaint():
    student = next(s for s in DB['students'] if s['id'] == session['user_id'])
    
    if 'complaints' not in DB:
        DB['complaints'] = []

    if request.method == 'POST':
        DB['complaints'].append({
            "student_id": student['id'],
            "name": student['name'],
            "room_no": student.get('room', 'Not Allocated'),
            "message": request.form['message'],
            "date": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "status": "Pending",
            "reply": "",
            "replied_on": ""
        })
        save_db(DB)
        flash("Complaint submitted successfully!", "success")
        return redirect(url_for('student_home'))

    return render_template('student/add_complaint.html', student=student)

# === VIEW COMPLAINTS ===
@app.route('/student/view_complaints')
@role_required('student')
def view_complaints():
    student = next(s for s in DB['students'] if s['id'] == session['user_id'])
    my_complaints = [c for c in DB.get('complaints', []) if c['student_id'] == student['id']]
    return render_template('student/view_complaints.html', complaints=my_complaints, student=student)

# === VIEW HOSTEL RULES ===
@app.route('/student/rules')
@role_required('student')
def hostel_rules():
    student = next(s for s in DB['students'] if s['id'] == session['user_id'])
    return render_template('student/rules.html', student=student)

# === WARDEN DASHBOARD ===
@app.route('/warden')
@role_required('warden')
def warden_dashboard():
    return render_template('dashboard/warden.html', db=DB, session=session)

# === WARDEN MODULES ===
@app.route('/warden/students')
@role_required('warden')
def warden_students():
    return render_template('warden/students.html', db=DB)

@app.route('/warden/rooms')
@role_required('warden')
def warden_rooms():
    return render_template('warden/rooms.html', db=DB)

@app.route('/warden/matrons')
@role_required('warden')
def warden_matrons():
    return render_template('warden/matrons.html', db=DB)

@app.route('/warden/payments')
@role_required('warden')
def warden_payments():
    return render_template('warden/payments.html', db=DB)

@app.route('/warden/complaints')
@role_required('warden')
def warden_complaints():
    return render_template('warden/complaints.html', complaints=DB['complaints'])

# === MATRON DASHBOARD ===
@app.route('/matron')
@role_required('matron')
def matron_dashboard():
    return render_template('dashboard/matron.html', session=session, db=DB)

# === MATRON ROUTES (all your existing ones) ===
@app.route('/matron/applications')
@role_required('matron')
def matron_applications():
    return render_template('matron/applications.html', applications=DB['applications'], rooms=DB['rooms'])

@app.route('/matron/view_application/<int:app_index>')
@role_required('matron')
def matron_view_application(app_index):
    if 0 <= app_index < len(DB['applications']):
        app = DB['applications'][app_index]
        return render_template('matron/view_application.html', app=app)
    flash("Application not found!", "danger")
    return redirect(url_for('matron_applications'))

@app.route('/matron/approve_application/<int:app_index>', methods=['GET', 'POST'])
@role_required('matron')
def matron_approve_application(app_index):
    if 0 <= app_index < len(DB['applications']):
        app = DB['applications'][app_index]
        if request.method == 'POST':
            room_no = request.form['room_no']
            room = next((r for r in DB['rooms'] if r['room_no'] == room_no and r['occupied'] < r['capacity']), None)
            if room:
                student = next(s for s in DB['students'] if s['id'] == app['student_id'])
                student['room'] = room_no
                room['occupied'] += 1
                if 'students' not in room: room['students'] = []
                room['students'].append(student['name'])
                app['status'] = "Approved"
                app['allocated_room'] = room_no
                flash(f"Room {room_no} allocated to {student['name']} by Matron!", "success")
            else:
                flash("Selected room is no longer available!", "danger")
            save_db(DB)
            return redirect(url_for('matron_applications'))
        return render_template('matron/approve_form.html', app=app, rooms=DB['rooms'], index=app_index)
    return redirect(url_for('matron_applications'))

@app.route('/matron/reject_application/<int:app_index>')
@role_required('matron')
def matron_reject_application(app_index):
    if 0 <= app_index < len(DB['applications']):
        DB['applications'][app_index]['status'] = "Rejected"
        save_db(DB)
        flash("Application rejected by Matron.", "info")
    return redirect(url_for('matron_applications'))

@app.route('/matron/rooms')
@role_required('matron')
def matron_rooms():
    return render_template('matron/rooms.html', db=DB)

@app.route('/matron/add_room', methods=['POST'])
@role_required('matron')
def matron_add_room():
    room_no = request.form['room_no']
    capacity = int(request.form['capacity'])
    if any(r['room_no'] == room_no for r in DB['rooms']):
        flash("Room already exists!", "danger")
    else:
        DB['rooms'].append({"room_no": room_no, "capacity": capacity, "occupied": 0, "students": []})
        save_db(DB)
        flash("Room added successfully!", "success")
    return redirect(url_for('matron_rooms'))

@app.route('/matron/edit_room_capacity', methods=['POST'])
@role_required('matron')
def matron_edit_room_capacity():
    room_no = request.form['room_no']
    new_capacity = int(request.form['capacity'])
    room = next((r for r in DB['rooms'] if r['room_no'] == room_no), None)
    if room:
        if new_capacity < room['occupied']:
            flash(f"Cannot reduce below occupied ({room['occupied']})!", "danger")
        else:
            room['capacity'] = new_capacity
            save_db(DB)
            flash(f"Room {room_no} capacity updated!", "success")
    return redirect(url_for('matron_rooms'))

@app.route('/matron/delete_room', methods=['POST'])
@role_required('matron')
def matron_delete_room():
    room_no = request.form.get('room_no')
    if room_no:
        DB['rooms'] = [r for r in DB['rooms'] if r['room_no'] != room_no]
        for student in DB['students']:
            if student.get('room') == room_no:
                student['room'] = None
        save_db(DB)
        flash(f"Room {room_no} deleted!", "success")
    return redirect(url_for('matron_rooms'))

@app.route('/matron/complaints')
@role_required('matron')
def matron_complaints():
    return render_template('matron/complaints.html', complaints=DB['complaints'])

@app.route('/matron/reply_complaint/<int:comp_index>', methods=['POST'])
@role_required('matron')
def matron_reply_complaint(comp_index):
    if 0 <= comp_index < len(DB['complaints']):
        DB['complaints'][comp_index]['reply'] = request.form['reply']
        DB['complaints'][comp_index]['status'] = "Forwarded to Warden"
        DB['complaints'][comp_index]['replied_on'] = datetime.now().strftime("%d-%m-%Y %H:%M")
        save_db(DB)
        flash("Reply sent and forwarded to Warden!", "success")
    return redirect(url_for('matron_complaints'))

@app.route('/matron/payments')
@role_required('matron')
def matron_payments():
    return render_template('matron/payments.html', db=DB)

@app.route('/matron/reports')
@role_required('matron')
def matron_reports():
    return render_template('matron/reports.html', db=DB)

# === STUDENT: VACATE REQUEST ===
@app.route('/student/vacate_request', methods=['GET', 'POST'])
@role_required('student')
def student_vacate_request():
    student = next(s for s in DB['students'] if s['id'] == session['user_id'])
    
    if not student.get('room'):
        flash("You are not allocated any room!", "danger")
        return redirect(url_for('student_home'))

    if request.method == 'POST':
        reason = request.form['reason']
        vacate_req = {
            "student_id": student['id'],
            "name": student['name'],
            "room_no": student['room'],
            "reason": reason,
            "status": "Pending",
            "requested_on": datetime.now().strftime("%d-%m-%Y")
        }
        if 'vacate_requests' not in DB:
            DB['vacate_requests'] = []
        DB['vacate_requests'].append(vacate_req)
        save_db(DB)
        flash("Vacate request sent to Matron!", "success")
        return redirect(url_for('student_home'))

    return render_template('student/vacate_request.html', student=student)

# === MATRON: VACATE REQUESTS ===
@app.route('/matron/vacate_requests')
@role_required('matron')
def matron_vacate_requests():
    vacate_requests = DB.get('vacate_requests', [])
    return render_template('matron/vacate_requests.html', vacate_requests=vacate_requests)

@app.route('/matron/approve_vacate/<int:req_index>')
@role_required('matron')
def matron_approve_vacate(req_index):
    if 0 <= req_index < len(DB.get('vacate_requests', [])):
        req = DB['vacate_requests'][req_index]
        student = next(s for s in DB['students'] if s['id'] == req['student_id'])
        room = next(r for r in DB['rooms'] if r['room_no'] == req['room_no'])
        
        student['room'] = None
        room['occupied'] -= 1
        if student['name'] in room['students']:
            room['students'].remove(student['name'])
        
        req['status'] = "Approved"
        save_db(DB)
        flash(f"Vacate request approved for {student['name']}", "success")
    return redirect(url_for('matron_vacate_requests'))

@app.route('/matron/reject_vacate/<int:req_index>')
@role_required('matron')
def matron_reject_vacate(req_index):
    if 0 <= req_index < len(DB.get('vacate_requests', [])):
        DB['vacate_requests'][req_index]['status'] = "Rejected"
        save_db(DB)
        flash("Vacate request rejected", "info")
    return redirect(url_for('matron_vacate_requests'))

@app.route('/matron/students_list')
@role_required('matron')
def matron_students_list():
    return render_template('matron/students_list.html', students=DB['students'])

@app.route('/matron/chat_warden', methods=['GET', 'POST'])
@role_required('matron')
def matron_chat_warden():
    if request.method == 'POST':
        message = request.form['message']
        flash(f"Message sent to Warden: {message}", "success")
        return redirect(url_for('matron_chat_warden'))
    return render_template('matron/chat_warden.html')

# === WARDEN: MANAGE MATRONS ===
@app.route('/warden/add_matron', methods=['POST'])
@role_required('warden')
def warden_add_matron():
    name = request.form['name'].strip()
    username = request.form['username'].strip().lower()
    password = request.form['password']
    contact = request.form['contact'].strip()

    if any(m['username'] == username for m in DB['matrons']):
        flash("Username already taken!", "danger")
    else:
        new_id = max([m['id'] for m in DB['matrons']], default=0) + 1
        DB['matrons'].append({
            "id": new_id,
            "name": name,
            "username": username,
            "password": password,
            "contact": contact
        })
        save_db(DB)
        flash(f"Matron '{name}' added successfully!", "success")
    return redirect(url_for('warden_matrons'))

@app.route('/warden/update_matron/<int:matron_id>', methods=['POST'])
@role_required('warden')
def warden_update_matron(matron_id):
    matron = next((m for m in DB['matrons'] if m['id'] == matron_id), None)
    if not matron:
        flash("Matron not found!", "danger")
        return redirect(url_for('warden_matrons'))

    name = request.form['name'].strip()
    username = request.form['username'].strip().lower()
    password = request.form.get('password', '').strip()
    contact = request.form['contact'].strip()

    if any(m['username'] == username and m['id'] != matron_id for m in DB['matrons']):
        flash("Username already taken!", "danger")
    else:
        matron['name'] = name
        matron['username'] = username
        if password:
            matron['password'] = password
        matron['contact'] = contact
        save_db(DB)
        flash(f"Matron '{name}' updated successfully!", "success")
    return redirect(url_for('warden_matrons'))

@app.route('/warden/delete_matron/<int:matron_id>')
@role_required('warden')
def warden_delete_matron(matron_id):
    DB['matrons'] = [m for m in DB['matrons'] if m['id'] != matron_id]
    save_db(DB)
    flash("Matron deleted successfully!", "success")
    return redirect(url_for('warden_matrons'))

# === WARDEN: REPORTS PAGE (REMOVED) ===
@app.route('/warden/reports')
@role_required('warden')
def warden_reports():
    flash("Reports module has been removed.", "info")
    return redirect(url_for('warden_dashboard'))

# NOTE: PDF generation and individual report routes have been removed as requested.

# === RUN APP ===
if __name__ == '__main__':
    app.run(debug=True)