#!/usr/bin/env python3
"""
Converting text to audio using lightweight pyttsx3 library.
Writes audio files using system's built-in TTS engine.
"""

import pyttsx3
from flask import session
import os
from pathlib import Path
import tempfile
import shutil

BASE_DIR = Path(__file__).parent.parent
AUDIO_FOLDER = BASE_DIR / "static" / "audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

def initialize_tts():
    """Initialize the text-to-speech engine"""
    engine = pyttsx3.init()
    
    # Configure voice settings for better quality
    voices = engine.getProperty('voices')
    female_voice_found = False
    
    if voices:
        # Try to use a female voice if available, otherwise use default
        for voice in voices:
            if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
    
    # Set speech rate (words per minute) - 2x speed increase
    engine.setProperty('rate', 150)  # Increased from 150 to 300 (2x speed)
    
    # Set volume (0.0 to 1.0)
    engine.setProperty('volume', 1.0)
    
    return engine

def convert_text_to_audio(text):
    """
    Convert text to audio and save as WAV file
    
    Args:
        text (str): Text to convert to speech
    """
    try:
        engine = initialize_tts()
        
        # Generate unique filename
        audio_filename = f"{session.get('user_id')}_audio.wav"
        output_filename = os.path.join(AUDIO_FOLDER, audio_filename)
        
        # Save audio to file
        engine.save_to_file(text, output_filename)
        engine.runAndWait()
        
        # Clean up engine resources
        engine.stop()
        
        return audio_filename
        
    except Exception as e:
        print(f"Error in text-to-speech conversion: {e}")
        # Return None if TTS fails - the frontend can handle this gracefully
        return None
