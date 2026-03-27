"""
ElevenLabs text-to-speech helpers.

This module wraps the ElevenLabs HTTP API and returns raw MP3 audio bytes.
If no API key is configured, it safely returns None so the application can
fall back to Twilio's built-in <Say> voice synthesis.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
DEFAULT_MODEL_ID = "eleven_turbo_v2_5"


def get_elevenlabs_voice_id() -> str:
    """Return the configured ElevenLabs voice ID, or a sensible default."""
    return os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)


def synthesize_speech(text: str, voice_id: Optional[str] = None) -> Optional[bytes]:
    """
    Generate MP3 audio from text using ElevenLabs.

    Returns:
        Raw audio bytes when synthesis succeeds.
        None when ElevenLabs is not configured or synthesis fails.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        logger.info("ELEVENLABS_API_KEY not set; falling back to Twilio <Say>")
        return None

    if not text or not text.strip():
        logger.warning("No text supplied for ElevenLabs synthesis")
        return None

    resolved_voice_id = voice_id or get_elevenlabs_voice_id()
    url = ELEVENLABS_API_URL.format(voice_id=resolved_voice_id)

    payload = {
        "text": text,
        "model_id": DEFAULT_MODEL_ID,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.8,
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException as exc:
        logger.error("ElevenLabs TTS request failed: %s", exc)
        return None
