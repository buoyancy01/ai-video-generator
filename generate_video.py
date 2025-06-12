# generate_video.py

import os
import requests
import time

PLAYHT_API_KEY = os.getenv("PLAYHT_API_KEY")
PLAYHT_USER_ID = os.getenv("PLAYHT_USER_ID")
DID_API_KEY = os.getenv("DID_API_KEY")

def generate_playht_audio(script_text: str) -> str:
    """Generates audio from script using Play.ht and returns audio URL."""
    headers = {
        "Authorization": f"Bearer {PLAYHT_API_KEY}",
        "X-User-Id": PLAYHT_USER_ID,
        "Content-Type": "application/json",
    }
    body = {
        "voice": "en-US-Wavenet-J",
        "content": [script_text],
        "title": "Product Script",
    }

    response = requests.post("https://api.play.ht/api/v2/tts", headers=headers, json=body)
    if response.status_code != 201:
        raise Exception(f"Error generating audio: {response.status_code}: {response.text}")

    transcription_id = response.json()["id"]

    # Wait for generation
    audio_url = None
    for _ in range(30):  # max 30 seconds wait
        poll = requests.get(f"https://api.play.ht/api/v2/tts/{transcription_id}", headers=headers)
        if poll.status_code == 200 and poll.json().get("audioUrl"):
            audio_url = poll.json()["audioUrl"]
            break
        time.sleep(2)

    if not audio_url:
        raise Exception("Audio generation timed out.")

    return audio_url


def generate_ai_video(script_text: str) -> str:
    """Generates a video with a talking avatar and returns video URL."""
    # Step 1: Generate audio
    audio_url = generate_playht_audio(script_text)

    # Step 2: Generate avatar video using D-ID
    headers = {
        "Authorization": f"Bearer {DID_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "script": {
            "type": "audio",
            "audio_url": audio_url
        },
        "source_url": "https://create-images-results.d-id.com/DefaultPresenters/Noelle-Hi.png"
    }

    response = requests.post("https://api.d-id.com/talks", json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"D-ID video generation error: {response.status_code}: {response.text}")

    talk_id = response.json()["id"]

    # Poll for video readiness
    for _ in range(30):
        result = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers)
        if result.status_code == 200:
            result_data = result.json()
            if result_data.get("result_url"):
                return result_data["result_url"]
        time.sleep(2)

    raise Exception("D-ID video generation timed out.")
