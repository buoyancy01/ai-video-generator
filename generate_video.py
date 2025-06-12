import os
import aiohttp
import base64
import asyncio

# Read API keys from environment variables (Render)
D_ID_API_KEY = os.environ["DID_API_KEY"]
PLAYHT_API_KEY = os.environ["PLAYHT_API_KEY"]
PLAYHT_USER_ID = os.environ["PLAYHT_USER_ID"]

async def generate_tts(script: str) -> str:
    """Generate audio from script using Play.ht and return the audio URL."""
    url = "https://api.play.ht/api/v2/tts"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {PLAYHT_API_KEY}",
        "X-USER-ID": PLAYHT_USER_ID
    }
    payload = {
        "text": script,
        "voice": "en-US-JennyNeural",
        "output_format": "mp3"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as res:
            data = await res.json()
            if "url" not in data:
                raise Exception(f"Play.ht TTS failed: {data}")
            return data["url"]

async def create_did_talk(image_bytes: bytes, audio_url: str) -> str:
    """Send image and audio to D-ID and return the talk_id."""
    base64_img = base64.b64encode(image_bytes).decode("utf-8")
    url = "https://api.d-id.com/talks"
    headers = {
        "Authorization": f"Bearer {D_ID_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "script": {
            "type": "audio",
            "audio_url": audio_url
        },
        "source_image": base64_img
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as res:
            data = await res.json()
            if "id" not in data:
                raise Exception(f"D-ID error: {data}")
            return data["id"]

async def check_talk_status(talk_id: str) -> str:
    """Check D-ID video status and return the video URL if ready."""
    url = f"https://api.d-id.com/talks/{talk_id}"
    headers = {
        "Authorization": f"Bearer {D_ID_API_KEY}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as res:
            data = await res.json()
            return data.get("result_url", None)
