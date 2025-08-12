from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'One_Piece'

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def root():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        conn.close()

        if result and check_password_hash(result[0], password):
            session['username'] = username
            return redirect(url_for('main'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']

        if not username or not password or not confirm:
            flash("All fields are required")
        elif password != confirm:
            flash("Passwords do not match")
        else:
            try:
                hashed = generate_password_hash(password)
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
                conn.commit()
                conn.close()
                flash("Registration successful. Please log in.")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash("Username already exists")
    return render_template('register.html')

@app.route('/main')
def main():
    if 'username' in session:
        username = session['username']
        return render_template('main_page.html', username=username)
    else:
        return redirect(url_for('login'))

@app.route('/private')
def private():
    if 'username' in session:
        username = session['username']
        return render_template('private.html', username=username)
    else:
        return redirect(url_for('login'))


@app.route('/public')
def public():
    if 'username' in session:
        username = session['username']
        return render_template('public.html', username=username)
    else:
        return redirect(url_for('login'))

@app.route('/settings')
def settings():
    if 'username' in session:
        username = session['username']
        return render_template('settings.html', username=username)
    else:
        return redirect(url_for('login'))

@app.route('/routes')
def show_routes():
    routes = sorted([rule.endpoint for rule in app.url_map.iter_rules()])
    return '<br>'.join(routes)



if __name__ == '__main__':
    app.run(debug=True)
