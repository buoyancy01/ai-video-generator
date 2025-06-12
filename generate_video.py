import os
import requests
import time

playht_user_id = os.getenv("PLAYHT_USER_ID")
playht_api_key = os.getenv("PLAYHT_API_KEY")

def generate_playht_audio(text):
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "AUTHORIZATION": playht_api_key,
        "X-USER-ID": playht_user_id
    }

    # Use a default voice that is generally stable
    payload = {
        "voice": "en-US-Wavenet-D",  # simpler, built-in voice
        "output_format": "mp3",
        "text": text
    }

    try:
        # Request audio generation
        response = requests.post("https://play.ht/api/v2/tts", json=payload, headers=headers)
        if response.status_code != 200:
            print(f"[Play.ht ERROR] Status {response.status_code}: {response.text}")
            return None

        audio_id = response.json().get("id")
        if not audio_id:
            print("[Play.ht ERROR] No audio ID returned.")
            return None

        # Poll until audio is ready
        for _ in range(20):
            time.sleep(3)
            status_res = requests.get(f"https://play.ht/api/v2/tts/{audio_id}", headers=headers)
            status_json = status_res.json()
            status = status_json.get("status")

            if status == "complete":
                return status_json.get("audioUrl")
            elif status == "failed":
                print("[Play.ht ERROR] Audio generation failed:", status_json)
                return None

        print("[Play.ht ERROR] Timeout: audio not ready after polling.")
        return None

    except Exception as e:
        print("[Play.ht EXCEPTION]", str(e))
        return None
