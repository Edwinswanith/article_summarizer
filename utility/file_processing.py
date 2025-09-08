from flask import session
import os
import docx
from pathlib import Path
from utility.rag_processing import process_pdf_for_rag

BASE_DIR = Path(__file__).parent.parent
UPLOAD_FOLDER = BASE_DIR / "uploads"

def process_uploaded_file(file):
    """
    Saves the uploaded file and processes it to extract text and images.
    """
    filepath = os.path.join(UPLOAD_FOLDER, f"{session.get('user_id')}_" + file.filename)
    file.save(filepath)

    file_extension = os.path.splitext(file.filename.lower())[1]
    file_type = file_extension[1:]

    text_chunks, image_info, full_text, references = [], [], "", {}

    if file_type == 'pdf':
        text_chunks, image_info, full_text, references = process_pdf_for_rag(filepath, str(BASE_DIR))
    elif file_type in ['doc', 'docx']:
        doc = docx.Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        for i, para_text in enumerate(paragraphs):
            text_chunks.append({"text": para_text, "page": i + 1})

    return text_chunks, image_info, full_text, file_type, filepath, references
