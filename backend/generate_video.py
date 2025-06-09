import requests
import base64
import uuid
import time
import os # <--- ADD THIS LINE TO IMPORT THE OS MODULE

# --- IMPORTANT: These values will be read from Render's environment variables ---
playht_user_id = os.getenv("PLAYHT_USER_ID")
playht_api_key = os.getenv("PLAYHT_API_KEY")
did_api_key = os.getenv("DID_API_KEY")

# Basic validation for API keys
if not all([playht_user_id, playht_api_key, did_api_key]):
    print("WARNING: One or more API keys are missing! Ensure PLAYHT_USER_ID, PLAYHT_API_KEY, and DID_API_KEY are set as environment variables.")
    # In a production setup, you might want to raise an error or halt.
    # For now, the functions will likely fail gracefully if keys are None.

def generate_ai_video(image_path: str, script_text: str):
    # 1. Generate audio using Play.ht
    audio_url = generate_playht_audio(script_text)
    if not audio_url:
        print("Error: Failed to generate audio from Play.ht")
        return "Error generating audio"

    # 2. Encode image for D-ID
    try:
        with open(image_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"Error: Image file not found at {image_path}")
        return "Error: Image file not found"
    except Exception as e:
        print(f"Error encoding image: {e}")
        return "Error encoding image"

    headers = {
        "Authorization": f"Bearer {did_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "source_image": encoded_image,
        "script": {
            "type": "audio",
            "audio_url": audio_url
        }
    }

    try:
        print(f"Sending request to D-ID API for video generation...")
        response = requests.post("https://api.d-id.com/talks", json=payload, headers=headers)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        result = response.json()
        print(f"D-ID API response: {result}")
        if result.get("result_url"):
            return result.get("result_url")
        else:
            print(f"D-ID API did not return a result_url. Response: {result}")
            return f"Error: D-ID API response missing video URL. Details: {result}"

    except requests.exceptions.RequestException as e:
        print(f"Error calling D-ID API: {e}")
        return f"Error: D-ID API request failed - {e}"
    except Exception as e:
        print(f"An unexpected error occurred during D-ID video generation: {e}")
        return f"Error: Unexpected error during D-ID video generation - {e}"


def generate_playht_audio(text):
    if not playht_api_key or not playht_user_id:
        print("Play.ht API keys not configured. Cannot generate audio.")
        return None

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "AUTHORIZATION": playht_api_key,
        "X-USER-ID": playht_user_id
    }

    payload = {
        "voice": "s3://voice-cloning-zero-shot/ai_female_voice_1/manifest.json", # Or choose another voice
        "output_format": "mp3",
        "text": text,
        "speed": 1.0, # Optional: adjust speed
        "sample_rate": "24000" # Optional: high quality
    }

    try:
        print(f"Sending request to Play.ht API for audio generation...")
        response = requests.post("https://play.ht/api/v2/tts", json=payload, headers=headers)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        audio_id = response.json().get("id")
        if not audio_id:
            print(f"Play.ht API did not return an audio ID. Response: {response.json()}")
            return None

        print(f"Play.ht audio generation initiated with ID: {audio_id}. Polling for completion...")
        status = ""
        # Poll for up to 60 seconds (20 iterations * 3 seconds)
        for _ in range(20):
            time.sleep(3) # Wait 3 seconds between polls
            status_res = requests.get(f"https://play.ht/api/v2/tts/{audio_id}", headers=headers)
            status_res.raise_for_status()
            status_json = status_res.json()
            status = status_json.get("status")

            if status == "complete":
                audio_url = status_json.get("audioUrl")
                if audio_url:
                    print(f"Play.ht audio generation complete. URL: {audio_url}")
                    return audio_url
                else:
                    print(f"Play.ht status complete but audioUrl missing: {status_json}")
                    return None
            elif status == "error":
                print(f"Play.ht audio generation failed with status 'error'. Details: {status_json}")
                return None
            elif status == "processing" or status == "queued":
                continue # Continue polling
            else:
                print(f"Play.ht unknown status: {status_json}")
                return None

        print("Play.ht audio generation timed out.")
        return None # Return None if polling times out or status is not complete

    except requests.exceptions.RequestException as e:
        print(f"Error calling Play.ht API: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Play.ht audio generation: {e}")
        return None