import google.generativeai as genai
import os
from dotenv import load_dotenv

def initialize_gemini():
    """Initialize the Gemini API with API key"""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash-lite')

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
            Summarize the following text in no more than 500 words.
            The summary must cover all pages and sections—do not skip any page or content.
            Ensure all key points, main ideas, important details, supporting evidence, subtle implications, relationships between concepts, and notable conclusions from the entire document are included.
            The summary should be cohesive and fully reflect the complete content, but remain under 500 words.
            {text}
        """

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"