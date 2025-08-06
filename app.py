# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import os
from utility.pdf_to_audio import process_uploaded_file, summarize_text, convert_summary_to_audio
import time
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import timedelta

app = Flask(__name__)

# Get secret key from environment
secret_key = os.getenv("FLASK_SECRET_KEY")
if not secret_key:
    raise ValueError("Missing FLASK_SECRET_KEY in .env")

# Configure database
app.config.update(
    SQLALCHEMY_DATABASE_URI='sqlite:///users.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

# Initialize database
db = SQLAlchemy(app)

# SQLAlchemy session config
app.config.update(
    SESSION_TYPE="sqlalchemy",
    SECRET_KEY=secret_key,
    SESSION_SQLALCHEMY=db,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    SESSION_COOKIE_NAME="article_summarizer",
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True
)
Session(app)
# Create database tables
with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    summary = None
    audio_filename = None
    session['user_id'] = str(uuid.uuid4())
    if request.method == "POST":
        try:
            start_time = time.time()
            file = request.files["file"]
            if not file or file.filename == "":
                error = "No file selected. Please upload a document."
                return render_template("index.html", error=error)
                
            text_chunks, image_info, full_text, file_type, uploaded_filepath = process_uploaded_file(file)

            # Store file paths in session for cleanup
            session["uploaded_filepath"] = uploaded_filepath
            session["extracted_images"] = [img["path"] for img in image_info]

            if not full_text:
                error = "Could not extract text from file. Please ensure it is a valid and non-empty document."
            else:
                summary = summarize_text(full_text, text_chunks, image_info)
                audio_filename = convert_summary_to_audio(summary)
                session["audio_filename"] = audio_filename
            end_time = time.time()
            print(f"\nTime taken: {end_time - start_time} seconds")
        except Exception as e:
            error = str(e)
            
    return render_template("index.html", error=error, summary=summary, audio_filename=audio_filename)


@app.route('/clean_up')
def clean_up():
    # Clear session-specific files
    uploaded_filepath = session.pop("uploaded_filepath", None)
    extracted_images = session.pop("extracted_images", [])
    audio_filename = session.pop("audio_filename", None)

    if uploaded_filepath and os.path.exists(uploaded_filepath):
        os.remove(uploaded_filepath)

    for img_path in extracted_images:
        full_img_path = os.path.join(app.static_folder, img_path) # app.static_folder points to 'static' dir
        if os.path.exists(full_img_path):
            os.remove(full_img_path)

    if audio_filename:
        full_audio_path = os.path.join(app.static_folder, 'audio', audio_filename)
        if os.path.exists(full_audio_path):
            os.remove(full_audio_path)

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
