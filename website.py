from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
import os
import random

app = Flask(__name__)
app.secret_key = 'One_Piece'

@app.context_processor
def inject_background():
    return {'background': session.get('background', 'default-bg.jpg')}

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --------------------
# Database setup
# --------------------
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Images table
    c.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploader TEXT NOT NULL,
            privacy TEXT NOT NULL CHECK(privacy IN ('private', 'public'))
        )
    ''')

    # Add background column if it doesn't exist
    try:
        c.execute("ALTER TABLE users ADD COLUMN background TEXT DEFAULT 'background_red.jpg'")
    except sqlite3.OperationalError:
        pass  # column exists

    conn.commit()
    conn.close()


# --------------------
# Helper functions
# --------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row
    return conn

# --------------------
# Routes
# --------------------
@app.route('/')
def root():
    return redirect(url_for('login'))

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            return redirect(url_for('main'))
        else:
            flash("Invalid username or password")
    
    return render_template("login.html")

# Register
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
            conn = get_db_connection()
            try:
                hashed = generate_password_hash(password)
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
                conn.commit()
                flash("Registration successful. Please log in.")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash("Username already exists")
            finally:
                conn.close()
    return render_template('register.html')

# Serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Main page (public images only)
@app.route('/main')
def main():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    rows = conn.execute("SELECT filename, uploader, privacy FROM images WHERE privacy='public' ORDER BY id DESC").fetchall()

    images = []
    for row in rows:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], row['filename'])
        if os.path.exists(filepath):
            images.append((row['filename'], row['uploader'], row['privacy']))
        else:
            conn.execute("DELETE FROM images WHERE filename = ?", (row['filename'],))
            conn.commit()
    conn.close()
    return render_template('main_page.html', username=session['username'], images=images)

# Your media page (private + public)
@app.route('/media')
def media():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    rows = conn.execute("SELECT filename, privacy FROM images WHERE uploader = ?", (username,)).fetchall()

    images = []
    for row in rows:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], row['filename'])
        if os.path.exists(filepath):
            images.append((row['filename'], row['privacy']))
        else:
            conn.execute("DELETE FROM images WHERE filename = ?", (row['filename'],))
            conn.commit()
    conn.close()
    return render_template('your_media.html', username=username, images=images)

# Upload image
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('image')
        privacy = request.form.get('privacy')

        if not file or not privacy:
            flash("File and privacy setting are required.")
            return redirect(url_for('upload'))

        if file.filename == '':
            flash("No file selected.")
            return redirect(url_for('upload'))

        if not allowed_file(file.filename):
            flash("Invalid file type. Only images are allowed.")
            return redirect(url_for('upload'))

        safe_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)

        conn = get_db_connection()
        conn.execute("INSERT INTO images (filename, uploader, privacy) VALUES (?, ?, ?)", 
                     (unique_name, session['username'], privacy))
        conn.commit()
        conn.close()

        flash("Image uploaded successfully!")
        return redirect(url_for('media'))

    return render_template('upload.html')


# Inspiration wall
WORDS = [ "Creativity", "Passion", "Dream", "Vision", "Innovation",
    "Inspire", "Art", "Design", "Imagination", "Expression",
    # ... keep all words as before
]

@app.route("/inspiration", methods=["GET", "POST"])
def inspiration_wall_page():
    max_words = len(WORDS)
    default_count = 10
    if request.method == "POST":
        try:
            count = int(request.form.get("word_count") or request.form.get("count") or default_count)
            count = max(1, min(count, max_words))
        except ValueError:
            count = default_count
    else:
        count = default_count

    random_words = random.sample(WORDS, k=count)
    return render_template("inspiration_wall.html", words=random_words, max_words=max_words, default_count=count)


# --------------------
# Settings + change username/password
# --------------------
@app.route('/settings')
def settings():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    rows = conn.execute("SELECT filename, privacy FROM images WHERE uploader = ?", (username,)).fetchall()
    conn.close()
    return render_template("settings.html", username=username, images=rows)


@app.route('/change_username', methods=['POST'])
def change_username():
    if 'username' not in session:
        return redirect(url_for('login'))

    old_username = session['username']
    new_username = request.form['new_username'].strip()

    if not new_username:
        flash("Username cannot be empty.")
        return redirect(url_for('settings'))

    conn = get_db_connection()
    try:
        # Update the username in users table
        conn.execute("UPDATE users SET username = ? WHERE username = ?", (new_username, old_username))
        
        # Update the uploader field in images table for this user
        conn.execute("UPDATE images SET uploader = ? WHERE uploader = ?", (new_username, old_username))
        
        conn.commit()
        session['username'] = new_username
        flash("Username updated successfully, and all your uploads are now linked to your new username!")
    except sqlite3.IntegrityError:
        flash("Username already taken.")
    finally:
        conn.close()

    return redirect(url_for('settings'))



@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    current = request.form['current_password']
    new_pass = request.form['new_password']
    confirm = request.form['confirm_password']

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (session['username'],)).fetchone()

    if not check_password_hash(user['password'], current):
        flash("Current password is incorrect.")
    elif new_pass != confirm:
        flash("New passwords do not match.")
    else:
        hashed = generate_password_hash(new_pass)
        conn.execute("UPDATE users SET password = ? WHERE username = ?", (hashed, session['username']))
        conn.commit()
        flash("Password updated successfully!")

    conn.close()
    return redirect(url_for('settings'))


if __name__ == '__main__':
    app.run(debug=True)
