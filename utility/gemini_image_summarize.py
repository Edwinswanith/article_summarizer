import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
import time
import asyncio
import concurrent.futures
from google.api_core.exceptions import ResourceExhausted, RetryError

def initialize_gemini():
    """Initialize the Gemini API with API key"""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    genai.configure(api_key=api_key)
    
    # Use the correct model name for vision capabilities
    try:
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Failed to initialize gemini-1.5-flash: {e}")
        raise ValueError("Failed to initialize Gemini vision model. Please check your API access.")

def process_single_image(image_path, page_text=""):
    """Process a single image with its page text context and return its summary"""
    retries = 0
    max_retries = 3
    
    while retries < max_retries:
        try:
            # Verify image exists and can be opened
            if not os.path.exists(image_path):
                return f"Image not found: {os.path.basename(image_path)}"
            
            # Initialize model for this thread
            model = initialize_gemini()
            img = Image.open(image_path)
            
            # Create contextual prompt that includes page text
            if page_text.strip():
                prompt = f"""
                Analyze this image (chart, graph, table, or figure) in the context of the following page text.
                Provide a concise analysis that connects the visual content with the textual information.
                Focus on key numbers, trends, and how the image supports the text concepts.
                
                Page Text Context:
                {page_text}
                
                Please provide an integrated analysis in exactly 30 words or less that combines insights from both the image and the text.
                """
            else:
                prompt = "Analyze this image (chart, graph, table, or figure) and summarize its key insights in exactly 30 words or less, including important numbers and trends."
            
            response = model.generate_content([prompt, img])
            if response.text:
                return response.text.strip()
            else:
                return f"No response generated for image: {os.path.basename(image_path)}"
                
        except (ResourceExhausted, RetryError) as e:
            wait_time = 2 ** retries  # Exponential backoff
            print(f"API limit reached for image {os.path.basename(image_path)}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            retries += 1
            if retries == max_retries:
                print(f"Max retries reached for image {os.path.basename(image_path)}. Skipping image.")
                return f"API_LIMIT_EXCEEDED: {os.path.basename(image_path)}"
                
        except Exception as e:
            print(f"Error processing image {os.path.basename(image_path)}: {e}")
            return f"Processing error: {os.path.basename(image_path)}"

def gemini_image_summarize(image_paths, page_texts=None):
    """
    Summarize images using Gemini API in parallel with page text context.
    Args:
        image_paths (list): A list of paths to image files.
        page_texts (list, optional): A list of page texts corresponding to each image.
    Returns:
        list: A list of summarized text for each image, or a signal on failure.
    """
    if not image_paths:
        return []
    
    # If no page texts provided, use empty strings
    if page_texts is None:
        page_texts = [""] * len(image_paths)
    
    # Ensure page_texts list matches image_paths length
    if len(page_texts) != len(image_paths):
        print(f"Warning: page_texts length ({len(page_texts)}) doesn't match image_paths length ({len(image_paths)})")
        page_texts = page_texts + [""] * (len(image_paths) - len(page_texts))
    
    try:
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(image_paths))) as executor:
            # Submit all image processing tasks with page text context
            future_to_path = {
                executor.submit(process_single_image, path, page_text): path 
                for path, page_text in zip(image_paths, page_texts)
            }
            summaries = []
            
            # Collect results in order
            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    summaries.append((path, result))
                except Exception as e:
                    print(f"Thread execution failed for {os.path.basename(path)}: {e}")
                    summaries.append((path, f"Thread error: {os.path.basename(path)}"))
            
            # Sort results to maintain original order
            summaries.sort(key=lambda x: image_paths.index(x[0]))
            return [summary for _, summary in summaries]
                
    except Exception as e:
        print(f"Vision model initialization failed: {e}")
        # Return a more specific error message instead of generic unavailable
        return ["VISION_INITIALIZATION_FAILED"] * len(image_paths)
