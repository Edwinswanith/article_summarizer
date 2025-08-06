import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image

def initialize_gemini():
    """Initialize the Gemini API with API key"""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=api_key)
    # The official model name requires the 'models/' prefix. Use a fallback if the vision model isn't available.
    model_names = ["models/gemini-pro-vision", "models/gemini-1.0-pro-vision", "models/gemini-pro"]
    for name in model_names:
        try:
            return genai.GenerativeModel(name)
        except Exception:
            continue
    # If none of the preferred models are available, raise the last exception implicitly
    raise ValueError("No suitable Gemini vision model found. Please check your API access.")

def gemini_image_summarize(image_paths):
    """
    Summarize images using Gemini API.
    Args:
        image_paths (list): A list of paths to image files.
    Returns:
        list: A list of summarized text for each image, or a signal on failure.
    """
    try:
        model = initialize_gemini()
        # Heuristic to check if the loaded model actually supports vision.
        if "-vision" not in getattr(model, "_model_name", ""):
            return ["VISION_MODEL_UNAVAILABLE"] * len(image_paths)

        summaries = []
        for image_path in image_paths:
            try:
                img = Image.open(image_path)
                prompt = "Analyze the image (chart, graph, table) and summarize its key insights in under 100 words, including important numbers."
                # Add a timeout to prevent long hangs on unresponsive API calls
                response = model.generate_content([prompt, img], request_options={"timeout": 10})
                summaries.append(response.text)
            except Exception as e:
                # If any image fails with a core API error, assume all will fail.
                if "generateContent" in str(e) or "API key" in str(e):
                    return ["VISION_API_FAILED"] * len(image_paths)
                summaries.append(f"Could not process image: {os.path.basename(image_path)}")
        return summaries
    except Exception:
        # Catches errors from initialize_gemini or other setup issues.
        return ["VISION_MODEL_UNAVAILABLE"] * len(image_paths)

if __name__ == "__main__":
    # Example usage:
    # Make sure to have a "test_images" directory with some images for this to work.
    # test_image_paths = ["test_images/chart.png", "test_images/graph.jpg"]
    # print(gemini_image_summarize(test_image_paths))
    pass