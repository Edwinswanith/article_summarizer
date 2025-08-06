#!/usr/bin/env python3
"""
Converting text to audio using Hugging Face's MMS-TTS English model.
Writes a 16-bit PCM WAV file using the built-in 'wave' module.
"""

import numpy as np
import torch
import wave, contextlib
from transformers import pipeline
from flask import session
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
AUDIO_FOLDER = BASE_DIR / "static" / "audio"
os.makedirs(AUDIO_FOLDER, exist_ok=True)

def initialize_tts():
    """Initialize the text-to-speech pipeline"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return pipeline(
        task="text-to-speech",
        model="facebook/mms-tts-eng",
        device=device
    )   

def convert_text_to_audio(text):
    """
    Convert text to audio and save as WAV file
    
    Args:
        text (str): Text to convert to speech
    """
    tts = initialize_tts()
    
    # Generate audio from text
    out = tts(text)
    sr = out["sampling_rate"]
    audio = np.asarray(out["audio"], dtype=np.float32)

    # Convert float32 [-1,1] to int16 
    audio = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio * 32767).astype(np.int16)

    # Save as WAV file
    audio_filename = f"{session.get('user_id')}_audio.wav"
    output_filename = os.path.join(AUDIO_FOLDER, audio_filename)
    with contextlib.closing(wave.open(output_filename, "wb")) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_int16.tobytes())

    return audio_filename 