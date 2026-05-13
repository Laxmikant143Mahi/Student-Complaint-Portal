from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'complaint_portal_secret'

# Use /tmp directory for SQLite database in Vercel serverless environment (read-only filesystem)
DB_FILE = '/tmp/complaints.db' if os.environ.get('VERCEL') else 'complaints.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            roll_no TEXT NOT NULL,
            department TEXT NOT NULL,
            category TEXT NOT NULL,
            complaint TEXT NOT NULL
        )
    ''')
    try:
        c.execute("ALTER TABLE complaints ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Seed data if table is empty
    c.execute("SELECT COUNT(*) FROM complaints")
    if c.fetchone()[0] == 0:
        seed_complaints = [
            ('Anjali Dindure', 'anjali@example.com', '101', 'Computer Science', 'Hostel', 'The Wi-Fi in the hostel is very slow and disconnects frequently.'),
            ('Vishnavi Bura', 'vishnavi@example.com', '102', 'Computer Science', 'Academics', 'Need more reference books for the Machine Learning course in the library.')
        ]
        c.executemany('INSERT INTO complaints (name, email, roll_no, department, category, complaint) VALUES (?, ?, ?, ?, ?, ?)', seed_complaints)
        
        seed_students = [
            ('Anjali Dindure', 'anjali@example.com', 'password123'),
            ('Vishnavi Bura', 'vishnavi@example.com', 'password123')
        ]
        c.executemany('INSERT OR IGNORE INTO students (name, email, password) VALUES (?, ?, ?)', seed_students)

    conn.commit()
    conn.close()

# In Vercel, the app is imported as a module, so we must initialize the DB here
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO students (name, email, password) VALUES (?, ?, ?)',
                      (name, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('student_register.html', error="Email already exists.")
        conn.close()
        
        return redirect(url_for('student_login'))
    return render_template('student_register.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM students WHERE email = ? AND password = ?', (email, password))
        student = c.fetchone()
        conn.close()
        
        if student:
            session['student_logged_in'] = True
            session['student_name'] = student['name']
            session['student_email'] = student['email']
            return redirect(url_for('student'))
        else:
            return render_template('student_login.html', error="Invalid email or password")
            
    return render_template('student_login.html')

@app.route('/student_logout')
def student_logout():
    session.pop('student_logged_in', None)
    session.pop('student_name', None)
    session.pop('student_email', None)
    return redirect(url_for('index'))

@app.route('/student', methods=['GET', 'POST'])
def student():
    if not session.get('student_logged_in'):
        return redirect(url_for('student_login'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        roll_no = request.form.get('roll_no')
        department = request.form.get('department')
        category = request.form.get('category')
        complaint = request.form.get('complaint')
        
        email = session.get('student_email', '')
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO complaints (name, email, roll_no, department, category, complaint) VALUES (?, ?, ?, ?, ?, ?)',
                  (name, email, roll_no, department, category, complaint))
        conn.commit()
        conn.close()
        return render_template('student.html', success=True)
    return render_template('student.html', success=False)

@app.route('/principal_login', methods=['GET', 'POST'])
def principal_login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('principal'))
        else:
            return render_template('principal_login.html', error="Invalid username or password")
    return render_template('principal_login.html')

@app.route('/principal')
def principal():
    if not session.get('logged_in'):
        return redirect(url_for('principal_login'))
        
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all complaints
    c.execute('SELECT * FROM complaints')
    all_complaints = c.fetchall()
    
    # Get categories by majority
    c.execute('SELECT category, COUNT(*) as count FROM complaints GROUP BY category ORDER BY count DESC')
    categories = c.fetchall()
    
    conn.close()
    
    # Group complaints by category prioritizing majority
    grouped_complaints = {}
    for cat in categories:
        grouped_complaints[cat['category']] = []
        
    for comp in all_complaints:
        if comp['category'] in grouped_complaints:
            grouped_complaints[comp['category']].append(comp)
            
    return render_template('principal.html', grouped_complaints=grouped_complaints, categories=categories)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        init_db()
    app.run(debug=True, port=5000)
