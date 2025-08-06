from utility.gemini_summarize_tool import gemini_summarize
import time
import asyncio
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
import os

# image_summary_map: dict of page int to list of summary strings for images on that page
def summarize_text(full_text, text_chunks, image_info, image_summary_map, vision_failure_signal=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "GEMINI_API_KEY not found."

    # Combine full text with image summaries for the second-stage Gemini summarizer
    combined_text = full_text
    if image_summary_map:
        combined_text += "\n\n--- Image Summaries ---\n"
        for page, summaries in image_summary_map.items():
            for s in summaries:
                combined_text += f"Page {page}: {s}\n"

    summary_start_time = time.time()
    summary = gemini_summarize(combined_text)
    summary_end_time = time.time()
    count = len(summary.split())
    print(f"Summary generation time: {int(summary_end_time - summary_start_time)} seconds And Count: {count}")

    if not text_chunks:
        return [{"response": summary, "page": "N/A", "source_text": "Could not extract source text.", "images": []}]

    original_docs = [Document(p["text"], metadata={"page": p["page"]}) for p in text_chunks]

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", google_api_key=api_key
    )
    original_store = FAISS.from_documents(original_docs, embeddings)

    final_response_with_citations = []
    summarized_pages = set()

    for para in [p.strip() for p in summary.split("\n\n") if p.strip()]:
        try:
            match = original_store.similarity_search(para, k=1)[0]
            page_num = int(match.metadata["page"])
            
            page_images = [img["path"] for img in image_info if img["page"] == page_num]

            if page_num not in summarized_pages:
                final_response_with_citations.append(
                    {
                        "response": para,
                        "page": str(page_num),
                        "source_text": match.page_content,
                        "images": page_images,
                    }
                )
                summarized_pages.add(page_num)
            else:
                for item in final_response_with_citations:
                    if item["page"] == str(page_num):
                        item["response"] += "\n\n" + para
                        break

        except Exception as e:
            print(f"Similarity search failed for a paragraph: {e}")
            final_response_with_citations.append(
                {
                    "response": para,
                    "page": "not found",
                    "source_text": "Source text not found",
                    "images": [],
                }
            )

    # Inject image summaries into the final response, ensuring each page with images is represented
    if image_summary_map:
        for page, summaries in image_summary_map.items():
            joined_summary = "\n".join(summaries)

            # Try to find an existing entry for this page
            entry = next((item for item in final_response_with_citations if item["page"] == str(page)), None)

            page_images = [img["path"] for img in image_info if img["page"] == page]

            if entry:
                # Append image summary to existing text
                entry["response"] += "\n\nImage Summary:\n" + joined_summary
                # Merge images, avoid duplicates
                entry["images"] = list(set(entry["images"] + page_images))
            else:
                # Create a new entry for this page
                final_response_with_citations.append(
                    {
                        "response": "Image Summary:\n" + joined_summary,
                        "page": str(page),
                        "source_text": "Image content",
                        "images": page_images,
                    }
                )

    # Ensure all pages with images are included in the final response
    image_pages = {img['page'] for img in image_info}
    summary_pages = {int(item['page']) for item in final_response_with_citations if item['page'].isdigit()}
    missing_image_pages = image_pages - summary_pages

    for page_num in missing_image_pages:
        page_images = [img["path"] for img in image_info if img["page"] == page_num]
        
        # Consolidate all text from the missing page to display it.
        page_text_content = "\n".join([chunk['text'] for chunk in text_chunks if chunk['page'] == page_num]).strip()
        
        # Use the actual page text, or a placeholder if there is none.
        response_text = page_text_content if page_text_content else "This page primarily contains visual elements."
        source_text = page_text_content if page_text_content else "Content is visual."

        if page_images:
            final_response_with_citations.append({
                "response": response_text,
                "page": str(page_num),
                "source_text": source_text,
                "images": page_images,
            })

    # Sort the final response by page number
    final_response_with_citations.sort(key=lambda x: int(x['page']) if x['page'].isdigit() else float('inf'))
    
    return final_response_with_citations 