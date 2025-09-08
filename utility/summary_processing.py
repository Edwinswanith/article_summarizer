import os
import re
import asyncio
from collections import defaultdict

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from utility.gemini_summarize_tool import gemini_summarize


def _build_page_text_map(text_chunks):
    """Return page_text_map {page: full text} and page_docs for FAISS."""
    page_text_map = defaultdict(list)
    for chunk in text_chunks or []:
        page = int(chunk.get("page") or 0)
        txt = (chunk.get("text") or "").strip()
        if txt:
            page_text_map[page].append(txt)

    for p in list(page_text_map.keys()):
        page_text_map[p] = "\n\n".join(page_text_map[p]).strip()

    page_docs = [Document(page_content=txt, metadata={"page": page})
                 for page, txt in sorted(page_text_map.items()) if txt]

    return page_text_map, page_docs


def _choose_best_page_for_para(store, para, page_to_images, default_page=None):
    """Match paragraph to best page (prefer ones with images)."""
    if store is None:
        return default_page
    matches = store.similarity_search(para, k=5)
    if not matches:
        return default_page
    for m in matches:
        p = int(m.metadata.get("page", 0) or 0)
        if page_to_images.get(p):
            return p
    return int(matches[0].metadata.get("page", default_page) or (default_page or 0))


def summarize_text(full_text, text_chunks, image_info, image_summary_map, references=None):
    """
    Returns a list of dicts grouped by page:
    [
      {
        "page": "<page number or 'N/A'>",
        "response": "<all paragraphs for this page merged>",
        "source_text": "<full page text>",
        "images": ["images/...png", ...],
        "type": "unified"
      }
    ]
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY not found."

    page_text_map, page_docs = _build_page_text_map(text_chunks)

    # Build FAISS store for page alignment
    store = None
    if page_docs:
        try:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001", google_api_key=api_key
            )
            store = FAISS.from_documents(page_docs, embeddings)
        except Exception as e:
            print(f"FAISS build failed: {e}")
            store = None

    # Combine text + image insights
    combined_content = f"TEXT SUMMARY:\n{full_text}\n\nIMAGE INSIGHTS:\n"
    for page, summaries in sorted(image_summary_map.items()):
        for s in summaries:
            combined_content += f"- Page {page}: {s}\n"

    # Get unified Gemini summary (≥10 paras)
    unified_summary = gemini_summarize(combined_content, references=references, min_paragraphs=10)
    paragraphs = [p.strip() for p in unified_summary.split("\n\n") if p.strip()]

    # Map page → images
    page_to_images = defaultdict(list)
    for img in image_info or []:
        try:
            page_to_images[int(img.get("page") or 0)].append(img.get("path"))
        except Exception:
            continue

    all_images_ordered = [path for p in sorted(page_to_images.keys()) for path in page_to_images[p]]
    used_images = set()

    def _pop_first_unused_image_for_page(p):
        for path in page_to_images.get(p, []):
            if path and path not in used_images:
                used_images.add(path)
                return path
        return None

    def _pop_first_unused_image_any_page():
        for path in all_images_ordered:
            if path and path not in used_images:
                used_images.add(path)
                return path
        return None

    # --- Step 1: Assign each paragraph to a page ---
    para_page_map = defaultdict(list)
    for para in paragraphs:
        matched_page = _choose_best_page_for_para(store, para, page_to_images, default_page=None)
        if not matched_page:
            matched_page = "N/A"
        para_page_map[matched_page].append(para)

    # --- Step 2: Build final results grouped by page ---
    results = []
    for page, paras in sorted(para_page_map.items(), key=lambda x: str(x[0])):
        merged_paras = "\n\n".join(paras)

        para_images = []
        if page != "N/A":
            # Attach all images from this page
            for img in page_to_images.get(page, []):
                if img not in used_images:
                    used_images.add(img)
                    para_images.append(img)
        else:
            # If N/A, attach any unused image
            img = _pop_first_unused_image_any_page()
            if img:
                para_images.append(img)

        if page != "N/A" and page in page_text_map:
            source_text = page_text_map[page]
        else:
            source_text = "Source text not found."

        results.append({
            "page": str(page),
            "response": merged_paras,
            "source_text": source_text,
            "images": para_images,
            "type": "unified"
        })

    # Attach any leftover images to the last entry
    leftovers = [p for p in all_images_ordered if p not in used_images]
    if leftovers and results:
        results[-1]["images"].extend(leftovers)

    return results
