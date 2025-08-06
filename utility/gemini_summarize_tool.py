import google.generativeai as genai
import os
from dotenv import load_dotenv

def initialize_gemini():
    """Initialize the Gemini API with API key"""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=api_key)
    # Use a stable, generally-available text model.
    model_names = [
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "models/gemini-pro"
    ]
    for name in model_names:
        try:
            return genai.GenerativeModel(name)
        except Exception:
            continue
    raise ValueError("No suitable Gemini text model found. Check API access.")

def gemini_summarize(text):
    """
    Summarize text using Gemini API
    Args:
        text (str): Text content to summarize
    Returns:
        str: Summarized text
    """
    try:
        model = initialize_gemini()
        
        prompt = f"""
            Provide a detailed and comprehensive summary of the following text.
            The summary must cover all pages and sections—do not skip any page or content.
            Ensure all key points, main ideas, important details, supporting evidence, and notable conclusions from the entire document are included.
            The summary should be well-structured, cohesive, and fully reflect the complete content of the document.
            {text}
        """

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"