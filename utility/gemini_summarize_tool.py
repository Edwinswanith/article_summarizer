import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
from google.api_core.exceptions import ResourceExhausted
import re


def _replace_citations_with_references(text: str, references: dict) -> str:
    """Wrap citations like [1] with a span tag for hover UI."""
    if not references:
        return text

    def wrap_match(match):
        citation_str = match.group(1)
        return f'<span class="citation-hover" data-ref-id="{citation_str}">[{citation_str}]</span>'

    citation_pattern = re.compile(r'\[\s*([\d,\s\-]+?)\s*\]')
    return citation_pattern.sub(wrap_match, text)


def initialize_gemini():
    """Initialize the Gemini API with API key."""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    genai.configure(api_key=api_key)

    model_names = [
        "models/gemini-2.5-flash",
        "models/gemini-1.5-flash"
    ]
    last_err = None
    for name in model_names:
        try:
            return genai.GenerativeModel(name)
        except Exception as e:
            last_err = e
            continue
    raise ValueError(f"No suitable Gemini model found. Last error: {last_err}")


def _normalize_paragraphs(text: str) -> str:
    """Normalize newlines for clean paragraph splitting."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _force_min_paragraphs(text: str, min_paragraphs: int = 10) -> str:
    """Ensure summary has at least min_paragraphs by splitting sentences."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paras) >= min_paragraphs:
        return "\n\n".join(paras)

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if not sentences:
        return text

    chunk_size = max(1, len(sentences) // min_paragraphs)
    forced = []
    for i in range(0, len(sentences), chunk_size):
        forced.append(" ".join(sentences[i:i + chunk_size]).strip())
    forced = [p for p in forced if p]
    return "\n\n".join(forced[:max(min_paragraphs, len(forced))])


def gemini_summarize(text, references=None, min_paragraphs: int = 10):
    """
    Summarize text using Gemini API.
    Ensures at least `min_paragraphs` paragraphs.
    """
    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            model = initialize_gemini()
            prompt = f"""
You are an expert document analyst. Create a detailed academic-style summary.

REQUIREMENTS:
- Write AT LEAST {min_paragraphs} paragraphs (aim for 10–12).
- Each paragraph should cover a distinct theme or section.
- Integrate any visual insights into the prose naturally.
- Separate paragraphs with EXACTLY TWO newlines (\\n\\n).
- Keep in-text citations like [1], [3-5] where appropriate.

CONTENT TO SUMMARIZE:
{text}
            """.strip()

            response = model.generate_content(prompt)
            summary_text = response.text or ""

            # Remove explicit "Table/Figure" mentions
            summary_text = re.sub(r'\(?(?:Table|table)\s+\d+(?:\.\d+)?\.?\)?', '', summary_text)
            summary_text = re.sub(r'\(?(?:Figure|figure|Fig\.|fig\.)\s+\d+(?:\.\d+)?\.?\)?', '', summary_text)

            summary_text = _normalize_paragraphs(summary_text)
            summary_text = _force_min_paragraphs(summary_text, min_paragraphs)

            summary_text = _replace_citations_with_references(summary_text, references)
            return summary_text

        except ResourceExhausted as e:
            wait_time = 2 ** retries
            print(f"Quota exceeded, retrying in {wait_time} sec...")
            time.sleep(wait_time)
            retries += 1
            if retries == max_retries:
                return f"Error generating summary: Max retries reached - {str(e)}"
        except Exception as e:
            return f"Error generating summary: {str(e)}"