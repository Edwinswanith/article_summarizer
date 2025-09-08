from flask import session
import fitz  # PyMuPDF
import os
from pathlib import Path
import io
from PIL import Image
import uuid
import re


def _is_potential_logo(bbox, page_width, page_height, max_dim=80, corner_threshold=40):
    """
    Heuristically checks if a bounding box likely contains a logo.
    Criteria: Small size AND proximity to page corners AND aspect ratio.
    """
    x0, y0, x1, y1 = bbox
    width, height = x1 - x0, y1 - y0

    # Check size - logos are typically small
    if width > max_dim or height > max_dim:
        return False

    # Check aspect ratio - logos are usually not extremely elongated
    aspect_ratio = max(width, height) / min(width, height)
    if aspect_ratio > 4:  # Very elongated shapes are unlikely to be logos
        return False

    # Check proximity to corners - logos are typically in corners
    is_near_top_left = x0 < corner_threshold and y0 < corner_threshold
    is_near_top_right = (page_width - x1) < corner_threshold and y0 < corner_threshold
    is_near_bottom_left = x0 < corner_threshold and (page_height - y1) < corner_threshold
    is_near_bottom_right = (page_width - x1) < corner_threshold and (page_height - y1) < corner_threshold

    # Must be near a corner to be considered a logo
    is_near_corner = is_near_top_left or is_near_top_right or is_near_bottom_left or is_near_bottom_right
    
    # Additional check: if it's in the center area of the page, it's likely not a logo
    center_x = page_width / 2
    center_y = page_height / 2
    bbox_center_x = (x0 + x1) / 2
    bbox_center_y = (y0 + y1) / 2
    
    # If it's in the central 60% of the page, it's unlikely to be a logo
    if (0.2 * page_width < bbox_center_x < 0.8 * page_width and 
        0.2 * page_height < bbox_center_y < 0.8 * page_height):
        return False

    return is_near_corner

def _merge_rects(rects, inflation=5):
    """Helper to merge overlapping or nearby rectangles."""
    if not rects:
        return []
    
    # Inflate rects to merge adjacent ones
    rect_list = [r + (-inflation, -inflation, inflation, inflation) for r in rects]
    
    merged = True
    while merged:
        merged = False
        for i, r1 in enumerate(rect_list):
            if r1.is_empty:
                continue
            for j in range(i + 1, len(rect_list)):
                r2 = rect_list[j]
                if r2.is_empty:
                    continue
                if r1.intersects(r2):
                    rect_list[i] |= r2  # Union of rects
                    rect_list[j] = fitz.Rect()  # Mark as empty
                    merged = True
        if merged:
            rect_list = [r for r in rect_list if not r.is_empty]
    
    # Shrink back and return
    return [r + (inflation, inflation, -inflation, -inflation) for r in rect_list]

def extract_references_from_text(full_text: str) -> dict[int, dict]:
    """
    Extracts reference information (journal and year) from the "References" section
    of the document text. The keys in the dictionary will be the citation numbers.

    Args:
        full_text (str): The entire text content of the document.

    Returns:
        dict[int, dict]: A dictionary where keys are citation numbers (int) and values
                         are dictionaries containing 'journal' and 'year'.
                         Example: {1: {'journal': 'Journal Name', 'year': 'YYYY'}}
    """
    references = {}
    
    # Define a marker for the start of the references section.
    references_marker = "References"
    
    # Find the position of the references marker.
    start_idx = full_text.find(references_marker)

    if start_idx == -1:
        return {}

    references_section_text = full_text[start_idx + len(references_marker):].strip()

    # Find all reference numbers and their starting positions.
    matches = list(re.finditer(r"(\d+)\.\s", references_section_text))

    for i, match in enumerate(matches):
        ref_num = int(match.group(1))
        start_of_ref_text = match.end()

        if i + 1 < len(matches):
            # The end of the current reference text is the start of the next reference's number.
            end_of_ref_text = matches[i+1].start()
        else:
            # This is the last reference, so it goes to the end of the section.
            end_of_ref_text = len(references_section_text)

        # Extract the actual reference text.
        ref_text = references_section_text[start_of_ref_text:end_of_ref_text].strip()

        # Remove trailing [CrossRef] or [PubMed] tags and any leading/trailing whitespace
        ref_text = re.sub(r'\s*\[(?:CrossRef|PubMed)\]\s*$', '', ref_text).strip()

        references[ref_num] = {"full_text": ref_text}

    return references

def process_pdf_for_rag(pdf_path: str, base_output_dir: str) -> tuple[list[dict], list[dict], str, dict[int, dict]]:
    """
    Extracts text paragraphs and images (including vector-based charts) from a PDF, structured for RAG.

    Args:
        pdf_path (str): Path to the PDF file.
        base_output_dir (str): Base directory for saving output (e.g., images).

    Returns:
        tuple[list[dict], list[dict], str, dict[int, dict]]: A tuple containing:
            - A list of text paragraphs, where each element is a dictionary:
              {'text': 'paragraph text', 'page': page_number}
            - A list of image information, where each element is a dictionary:
              {'path': 'relative/path/to/image.png', 'page': page_number}
            - The full extracted text as a single string.
            - A dictionary of extracted references, where keys are citation numbers (int) and values
              are dictionaries containing 'journal' and 'year'.
    """
    doc = fitz.open(pdf_path)
    
    images_out_dir = Path(base_output_dir) / "static" / "images"
    os.makedirs(images_out_dir, exist_ok=True)

    text_chunks = []
    image_info = []
    full_text = ""
    references = {}

    for page_num, page in enumerate(doc, start=1):
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Define header and footer regions (e.g., top/bottom 8% of the page height)
        header_threshold = page_height * 0.08
        footer_threshold = page_height * 0.92

        # Extract text blocks with their bounding boxes
        text_blocks = page.get_text("dict")["blocks"]
        page_text_content = []

        for b in text_blocks:
            if b["type"] == 0:  # Text block
                block_text = []
                for l in b["lines"]:
                    line_text = []
                    for s in l["spans"]:
                        # Check if the text span is outside the header and footer regions
                        x0, y0, x1, y1 = s["bbox"]
                        if y1 > header_threshold and y0 < footer_threshold:
                            line_text.append(s["text"])
                    if line_text:
                        block_text.append(" ".join(line_text))
                
                if block_text:
                    # Join lines within a block with newlines to preserve structure
                    page_text_content.append("\n".join(block_text))
        
        # Join blocks with double newlines to create paragraph separations
        text = "\n\n".join(page_text_content).strip()
        if text:
            full_text += text + "\n\n"
            
            # Improved paragraph splitting - split by double newlines and filter meaningful chunks
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            
            for p in paragraphs:
                # Further split long paragraphs into smaller chunks if they're too long
                if len(p) > 1000:  # If paragraph is longer than 1000 characters
                    # Split by sentence endings, but keep sentences together
                    sentences = []
                    current_chunk = ""
                    
                    # Split by periods, exclamation marks, or question marks followed by space or newline
                    sentence_endings = re.split(r'([.!?])\s+', p)
                    
                    for i in range(0, len(sentence_endings), 2):
                        if i + 1 < len(sentence_endings):
                            sentence = sentence_endings[i] + sentence_endings[i + 1]
                        else:
                            sentence = sentence_endings[i]
                        
                        # If adding this sentence would make the chunk too long, save current chunk
                        if len(current_chunk) + len(sentence) > 800 and current_chunk:
                            text_chunks.append({"text": current_chunk.strip(), "page": page_num})
                            current_chunk = sentence
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
                    
                    # Add the last chunk if it has content
                    if current_chunk.strip():
                        text_chunks.append({"text": current_chunk.strip(), "page": page_num})
                else:
                    # For shorter paragraphs, add as-is but ensure minimum length
                    if len(p) > 50:  # Only add chunks with meaningful content
                        text_chunks.append({"text": p, "page": page_num})

        # --- Image and Drawing Extraction ---

        # 1. Extract raster images
        image_bboxes = []
        img_list = page.get_images(full=True)
        for img_index, img in enumerate(img_list):
            xref = img[0]
            try:
                bbox = page.get_image_bbox(img)
                if not bbox.is_empty:
                    image_bboxes.append(bbox)

                # Check if it's a potential logo before saving
                if _is_potential_logo(bbox, page.rect.width, page.rect.height):
                    continue
                
                pix = fitz.Pixmap(doc, xref)
                if pix.alpha:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                img_filename = f"{session.get('user_id')}_page{page_num}_img{img_index + 1}.png"
                img_path = images_out_dir / img_filename
                pix.save(str(img_path))
                
                web_path = os.path.join("images", img_filename).replace("\\", "/")
                image_info.append({"path": web_path, "page": page_num})
            except Exception as e:
                print(f"Error processing image xref {xref} on page {page_num}: {e}")
                continue

        # 2. Extract drawings (vector graphics like charts)
        drawings = page.get_drawings()
        if not drawings:
            continue
        
        drawing_rects = [d['rect'] for d in drawings if not d['rect'].is_empty]
        if not drawing_rects:
            continue
            
        merged_drawing_rects = _merge_rects(drawing_rects)
        
        chart_index = 1
        for rect in merged_drawing_rects:
            if rect.is_empty or rect.width < 40 or rect.height < 40:
                continue
            
            # Check for significant overlap with already extracted raster images
            is_part_of_existing_image = False
            for img_bbox in image_bboxes:
                intersect = rect & img_bbox
                if not intersect.is_empty:
                    if intersect.get_area() / rect.get_area() > 0.8:
                        is_part_of_existing_image = True
                        break
            if is_part_of_existing_image:
                continue

            # Check if it's a potential logo before saving - more restrictive for drawings
            if _is_potential_logo(rect, page.rect.width, page.rect.height, max_dim=60, corner_threshold=30):
                continue

            # Render the area of the drawing and save as an image
            try:
                clip_rect = rect.irect
                if clip_rect.is_empty: continue
                
                pix = page.get_pixmap(clip=clip_rect, dpi=150)
                if not pix.width or not pix.height:
                    continue

                # Heuristic to avoid saving blank images using Pillow
                try:
                    img_data = pix.tobytes("png")
                    if len(img_data) < 200:  # Small PNGs are often blank or tiny lines
                        continue

                    img = Image.open(io.BytesIO(img_data))
                    
                    colors = img.getcolors(img.width * img.height)
                    if colors:
                        # If the most dominant color covers > 99.5% of the image, it's likely blank
                        if (max(c[0] for c in colors) / (img.width * img.height)) > 0.995:
                            continue
                except Exception as e:
                    continue

                chart_filename = f"{session.get('user_id')}_page{page_num}_chart{chart_index}.png"
                chart_path = images_out_dir / chart_filename
                with open(str(chart_path), "wb") as f:
                    f.write(img_data)
                
                web_path = os.path.join("images", chart_filename).replace("\\", "/")
                image_info.append({"path": web_path, "page": page_num})
                chart_index += 1
            except Exception as e:
                print(f"Error processing drawing on page {page_num} at rect {rect}: {e}")

    references = extract_references_from_text(full_text)

    return text_chunks, image_info, full_text.strip(), references
