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
            roll_no TEXT NOT NULL,
            department TEXT NOT NULL,
            category TEXT NOT NULL,
            complaint TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# In Vercel, the app is imported as a module, so we must initialize the DB here
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/student', methods=['GET', 'POST'])
def student():
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        department = request.form['department']
        category = request.form['category']
        complaint = request.form['complaint']
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO complaints (name, roll_no, department, category, complaint) VALUES (?, ?, ?, ?, ?)',
                  (name, roll_no, department, category, complaint))
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
