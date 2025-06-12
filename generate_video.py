import os
import requests
import time
import uuid
from PIL import Image
import io
import json

AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION")
D_ID_API_KEY = os.getenv("D_ID_API_KEY")

def preprocess_image(image_bytes):
    """Converts image to JPEG for D-ID compatibility"""
    with Image.open(io.BytesIO(image_bytes)) as img:
        rgb_image = img.convert("RGB")
        output_buffer = io.BytesIO()
        rgb_image.save(output_buffer, format="JPEG")
        return output_buffer.getvalue()

def generate_azure_tts(script: str, voice: str = "en-US-AriaNeural") -> str:
    # Generate audio using Azure TTS
    token_url = f"https://{AZURE_TTS_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": AZURE_TTS_KEY, "Content-Length": "0"}
    
    # Get auth token
    token_response = requests.post(token_url, headers=headers)
    token_response.raise_for_status()
    access_token = token_response.text

    # Generate speech
    tts_url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    tts_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3"
    }
    ssml = f"""<speak version='1.0' xml:lang='en-US'><voice name='{voice}'>{script}</voice></speak>"""
    
    response = requests.post(tts_url, headers=tts_headers, data=ssml.encode('utf-8'))
    response.raise_for_status()
    
    # Save and host audio
    filename = f"audio_{uuid.uuid4().hex}.mp3"
    with open(filename, "wb") as f:
        f.write(response.content)
    
    return upload_to_tmpfiles(filename)  # Return public URL

def upload_to_tmpfiles(file_path: str) -> str:
    """Uploads file to temporary hosting service"""
    with open(file_path, 'rb') as f:
        response = requests.post(
            'https://tmpfiles.org/api/v1/upload',
            files={'file': (os.path.basename(file_path), f)}
        )
    os.remove(file_path)  # Clean up local file
    response.raise_for_status()
    return response.json()['data']['url']  # Return public URL

def create_did_talk(image_bytes, audio_url):
    """Create D-ID talk with proper authentication"""
    headers = {"Authorization": f"Bearer {D_ID_API_KEY}"}  # Fixed: Use Bearer token
    
    files = {"source_image": ("image.jpg", image_bytes, "image/jpeg")}
    data = {"script": json.dumps({"type": "audio", "audio_url": audio_url})}
    
    response = requests.post(
        "https://api.d-id.com/talks",
        headers=headers,
        files=files,
        data=data
    )
    response.raise_for_status()
    return response.json()["id"]

def check_talk_status(talk_id: str) -> str:
    """Check talk status with proper authentication"""
    headers = {"Authorization": f"Bearer {D_ID_API_KEY}"}  # Fixed: Use Bearer token
    
    for _ in range(30):  # Check for ~60 seconds
        response = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result_url"):
            return data["result_url"]
        time.sleep(2)
    
    raise Exception("Video generation timed out")
