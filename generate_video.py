# generate_video.py
import os
import aiohttp
import base64
import tempfile

D_ID_API_KEY = os.environ["D_ID_API_KEY"]
AZURE_TTS_KEY = os.environ["AZURE_TTS_KEY"]
AZURE_TTS_REGION = os.environ["AZURE_TTS_REGION"]

async def generate_tts(script: str) -> bytes:
    url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        "User-Agent": "AI-Video-Generator"
    }
    ssml = f"""
    <speak version='1.0' xml:lang='en-US'>
      <voice name='en-US-JennyNeural'>
        {script}
      </voice>
    </speak>
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=ssml.encode("utf-8"), headers=headers) as res:
            if res.status != 200:
                error_text = await res.text()
                raise Exception(f"Azure TTS failed: {error_text}")
            return await res.read()

async def create_did_talk(image_bytes: bytes, audio_bytes: bytes) -> str:
    base64_img = base64.b64encode(image_bytes).decode("utf-8")
    base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    url = "https://api.d-id.com/talks"
    headers = {
        "Authorization": f"Basic {D_ID_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "script": {
            "type": "audio",
            "audio": base64_audio
        },
        "source_image": base64_img
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as res:
            data = await res.json()
            if "id" not in data:
                raise Exception(f"D-ID error: {data}")
            return data["id"]

async def poll_did_video(talk_id: str) -> str:
    url = f"https://api.d-id.com/talks/{talk_id}"
    headers = {"Authorization": f"Bearer {D_ID_API_KEY}"}
    for _ in range(30):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as res:
                data = await res.json()
                if data.get("result_url"):
                    return data["result_url"]
        await asyncio.sleep(2)
    raise Exception("Timeout: D-ID video generation failed.")

async def generate_ai_video(image_bytes: bytes, script: str) -> str:
    audio_bytes = await generate_tts(script)
    talk_id = await create_did_talk(image_bytes, audio_bytes)
    video_url = await poll_did_video(talk_id)
    return video_url
