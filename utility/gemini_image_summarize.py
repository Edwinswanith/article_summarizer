import google.generativeai as genai
import os
from dotenv import load_dotenv
import fitz  # PyMuPDF
from PIL import Image

def initialize_gemini():
    """Initialize the Gemini API with API key"""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash-lite')


def gemini_image_summarize(images):
    """
    Summarize text using Gemini API
    Args:
        text (str): Text content to summarize
    Returns:
        str: Summarized text
    """
    try:
        model = initialize_gemini()
        summary = []
        for image in images:
            prompt = f"""
                Analyze the provided image and identify any charts, graphs, or visual data representations present within it. Focus on summarizing the content and key insights of these images or charts in clear, concise language. Your summary should highlight the main information, trends, or conclusions depicted, and be no longer than 100 words. If there are multiple charts or images, briefly mention each and their significance. Do not include irrelevant details—concentrate on the visual data and its meaning.
                The image is:
                {image}
            """

            response = model.generate_content(prompt)
            summary.append(response.text)
        return summary
        
    except Exception as e:
        return f"Error generating summary: {str(e)}"
    
if __name__ == "__main__":
    print(gemini_image_summarize("/home/bizzzup/Documents/Web_Application/Backup/25904633.pdf"))