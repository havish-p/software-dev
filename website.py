from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory, current_app
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import uuid
import os
import random

app = Flask(__name__)
app.secret_key = 'One_Piece'

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

    conn.commit()
    conn.close()

init_db()

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
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            try:
                hashed = generate_password_hash(password)
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
                conn.commit()
                flash("Registration successful. Please log in.")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash("Username already exists")
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
    rows = conn.execute("""
        SELECT filename, uploader, privacy
        FROM images
        WHERE privacy = 'public'
        ORDER BY id DESC
    """).fetchall()

    # Auto-clean missing files
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
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        rows = conn.execute("SELECT filename, privacy FROM images WHERE uploader = ?", (username,)).fetchall()

        # Auto-clean missing files
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
    else:
        return redirect(url_for('login'))

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

        # Create safe and unique filename
        safe_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO images (filename, uploader, privacy) VALUES (?, ?, ?)",
                  (unique_name, session['username'], privacy))
        conn.commit()
        conn.close()

        flash("Image uploaded successfully!")
        return redirect(url_for('media'))

    return render_template('upload.html')

# Inspiration wall
WORDS = [
    "Creativity", "Passion", "Dream", "Vision", "Innovation",
    "Inspire", "Art", "Design", "Imagination", "Expression",
    "Color", "Light", "Flow", "Energy", "Concept", "Hope",
    "Believe", "Strength", "Courage", "Balance", "Growth",
    "Harmony", "Peace", "Focus", "Mindset", "Change",
    "Transform", "Magic", "Spark", "Freedom", "Clarity",
    "Love", "Compassion", "Empathy", "Kindness", "Gratitude",
    "Patience", "Determination", "Discipline", "Resilience",
    "Joy", "Happiness", "Adventure", "Explore", "Journey",
    "Curiosity", "Wonder", "Discovery", "Potential", "Bravery",
    "Integrity", "Authenticity", "Trust", "Respect", "Wisdom",
    "Knowledge", "Learning", "Teaching", "Sharing", "Community",
    "Unity", "Together", "Support", "Collaboration", "Teamwork",
    "Leadership", "Challenge", "Opportunity", "Success", "Failure",
    "Persistence", "Dedication", "Commitment", "Excellence", "Ambition",
    "Focus", "Drive", "Momentum", "Flow", "Visionary",
    "Strategy", "Innovation", "Technology", "Future", "Possibility",
    "Limitless", "Boundless", "Faith", "Healing", "Nature",
    "Earth", "Sky", "Ocean", "Mountain", "River",
    "Forest", "Sun", "Moon", "Stars", "Galaxy",
    "Universe", "Energy", "Light", "Shadow", "Fire",
    "Water", "Air", "Earth", "Spirit", "Soul",
    "Heart", "Mind", "Body", "Connection", "Truth",
    "Beauty", "Artistry", "Simplicity", "Elegance", "Strength"
]


@app.route("/inspiration", methods=["GET", "POST"])
def inspiration_wall_page():
    max_words = len(WORDS)
    default_count = 10  # how many words to show initially

    if request.method == "POST":
        try:
            # handle both "word_count" and "count" form inputs
            count = int(
                request.form.get("word_count") or request.form.get("count") or default_count
            )
            count = max(1, min(count, max_words))  # clamp value safely
        except ValueError:
            count = default_count
    else:
        count = default_count

    random_words = random.sample(WORDS, k=count)
    return render_template(
        "inspiration_wall.html",
        words=random_words,
        max_words=max_words,
        default_count=count
    )

if __name__ == '__main__':
    app.run(debug=True)