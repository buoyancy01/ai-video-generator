import os
import requests
import time
import uuid
from PIL import Image
import io
import json

# Load environment variables
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
    """Generate TTS audio and return public URL"""
    # Get Azure auth token
    token_url = f"https://{AZURE_TTS_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    token_response = requests.post(token_url, headers={
        "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
        "Content-Length": "0"
    })
    token_response.raise_for_status()
    access_token = token_response.text
    
    # Generate speech
    tts_url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    response = requests.post(
        tts_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3"
        },
        data=f"<speak version='1.0' xml:lang='en-US'><voice name='{voice}'>{script}</voice></speak>"
    )
    response.raise_for_status()
    
    # Save and host audio
    filename = f"audio_{uuid.uuid4().hex}.mp3"
    with open(filename, "wb") as f:
        f.write(response.content)
    
    return upload_to_tmpfiles(filename)

def upload_to_tmpfiles(file_path: str) -> str:
    """Uploads file to temporary hosting with error handling"""
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(
                'https://tmpfiles.org/api/v1/upload',
                files={'file': (os.path.basename(file_path), f)}
            )
        response.raise_for_status()
        return response.json()['data']['url']
    finally:
        os.remove(file_path)  # Clean up regardless of success

def create_did_talk(image_bytes, audio_url):
    """Create D-ID talk with enhanced error handling"""
    headers = {"Authorization": f"Bearer {D_ID_API_KEY}"}
    
    # Debug: Log API key (masked) and audio URL
    print(f"D-ID API Key: {D_ID_API_KEY[:5]}...{D_ID_API_KEY[-3:]}")
    print(f"Audio URL: {audio_url}")
    
    try:
        response = requests.post(
            "https://api.d-id.com/talks",
            headers=headers,
            files={"source_image": ("image.jpg", image_bytes, "image/jpeg")},
            data={"script": json.dumps({"type": "audio", "audio_url": audio_url})}
        )
        
        # Capture detailed error info
        if response.status_code != 201:
            error_details = {
                "status": response.status_code,
                "headers": dict(response.headers),
                "response": response.text
            }
            raise Exception(f"D-ID API Error: {json.dumps(error_details)}")
            
        return response.json()["id"]
    except Exception as e:
        raise Exception(f"Failed to create talk: {str(e)}")

def check_talk_status(talk_id: str) -> str:
    """Check talk status with proper authentication"""
    headers = {"Authorization": f"Bearer {D_ID_API_KEY}"}
    
    for i in range(30):
        response = requests.get(
            f"https://api.d-id.com/talks/{talk_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "done" and data.get("result_url"):
                return data["result_url"]
        
        print(f"Check #{i+1}: Status {response.status_code}")
        time.sleep(2)
    
    raise Exception("Video generation timed out after 60 seconds")
