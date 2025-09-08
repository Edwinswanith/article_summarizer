# app.py
import os
# Fix OpenMP runtime conflict before any imports that use OpenMP
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from flask import Flask, render_template, request, redirect, url_for, session
import time
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
import uuid
from dotenv import load_dotenv
from datetime import timedelta
from utility.file_processing import process_uploaded_file
from utility.summary_processing import summarize_text
from utility.audio_processing import convert_text_to_audio
from utility.gemini_image_summarize import gemini_image_summarize
load_dotenv()

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
    references = {}
    session['user_id'] = str(uuid.uuid4())
    if request.method == "POST":
        try:
            start_time = time.time()
            file = request.files["file"]
            if not file or file.filename == "":
                error = "No file selected. Please upload a document."
                return render_template("index.html", error=error)
                
            text_chunks, image_info, full_text, file_type, uploaded_filepath, references = process_uploaded_file(file)

            # Store file paths in session for cleanup
            session["uploaded_filepath"] = uploaded_filepath
            session["extracted_images"] = [img["path"] for img in image_info]

            if not full_text:
                error = "Could not extract text from file. Please ensure it is a valid and non-empty document."
            else:
                # Generate summaries for each extracted image using absolute file paths with page text context
                image_full_paths = [os.path.join(app.static_folder, p) for p in session["extracted_images"]]
                
                # Create page text mapping for images
                image_page_texts = []
                for img_info in image_info:
                    page_num = img_info["page"]
                    # Get all text from this page
                    page_text = "\n".join([chunk['text'] for chunk in text_chunks if chunk['page'] == page_num])
                    image_page_texts.append(page_text)
                
                image_summaries = gemini_image_summarize(image_full_paths, image_page_texts)
                print(f"\nImage summaries: {image_summaries}\n")
                # Check for a global failure signal from the vision model
                vision_failure_signal = None
                if image_summaries and image_summaries[0].startswith("VISION_"):
                    vision_failure_signal = image_summaries[0]
                
                # Build a mapping from page -> list of image summaries, only if vision didn't fail
                page_image_summary_map = {}
                if not vision_failure_signal:
                    for info, img_sum in zip(image_info, image_summaries):
                        p = info["page"]
                        page_image_summary_map.setdefault(p, []).append(img_sum)

                summary = summarize_text(
                    full_text, text_chunks, image_info, page_image_summary_map, 
                    references=references
                )
                
                if isinstance(summary, list):
                    summary_text = "\n".join([item['response'] for item in summary])
                else:
                    summary_text = summary
                
                audio_filename = convert_text_to_audio(summary_text)
                if audio_filename:
                    session["audio_filename"] = audio_filename
                
            end_time = time.time()
            print(f"\nTime taken: {end_time - start_time} seconds")
        except Exception as e:
            error = str(e)
            
    return render_template("index.html", error=error, summary=summary, audio_filename=audio_filename, references=references)

@app.route('/clean_up')
def clean_up():
    # Clear session-specific files
    uploaded_filepath = session.pop("uploaded_filepath", None)
    extracted_images = session.pop("extracted_images", [])
    audio_filename = session.pop("audio_filename", None)

    if uploaded_filepath and os.path.exists(uploaded_filepath):
        os.remove(uploaded_filepath)

    for img_path in extracted_images:
        full_img_path = os.path.join(app.static_folder, img_path)
        if os.path.exists(full_img_path):
            os.remove(full_img_path)

    if audio_filename:
        full_audio_path = os.path.join(app.static_folder, 'audio', audio_filename)
        if os.path.exists(full_audio_path):
            os.remove(full_audio_path)

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True, port=8000)
