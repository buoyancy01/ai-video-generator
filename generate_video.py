import os
import requests
import time
import uuid
from PIL import Image
import io
import json

# Load environment variables with validation
AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION")
D_ID_API_KEY = os.getenv("D_ID_API_KEY")
D_ID_REGION = os.getenv("D_ID_REGION", "global")  # global or eu

# Determine D-ID base URL based on region
D_ID_BASE_URL = "https://api.d-id.com" if D_ID_REGION == "global" else "https://eu-api.d-id.com"

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
    ssml = f"<speak version='1.0' xml:lang='en-US'><voice name='{voice}'>{script}</voice></speak>"
    
    response = requests.post(
        tts_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3"
        },
        data=ssml.encode('utf-8')
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
                'https://file.io',
                files={'file': (os.path.basename(file_path), f)}
            )
        response.raise_for_status()
        return response.json()['link']
    finally:
        try:
            os.remove(file_path)  # Clean up
        except:
            pass

def create_did_talk(image_bytes, audio_url):
    """Create D-ID talk with enhanced authentication"""
    headers = {
        "Authorization": f"Bearer {D_ID_API_KEY}",
        "Content-Type": "multipart/form-data"
    }
    
    # Create form data payload
    files = {
        "source_image": ("image.jpg", image_bytes, "image/jpeg")
    }
    
    data = {
        "script": json.dumps({
            "type": "audio",
            "audio_url": audio_url,
            "subtitles": False
        })
    }
    
    try:
        response = requests.post(
            f"{D_ID_BASE_URL}/talks",
            headers=headers,
            files=files,
            data=data
        )
        
        if response.status_code == 401:
            # Special handling for authentication issues
            raise Exception(f"D-ID Authentication Failed: Check API Key and Region")
        
        response.raise_for_status()
        return response.json()["id"]
    except requests.exceptions.RequestException as e:
        error_details = {
            "status": e.response.status_code if e.response else "No response",
            "error": str(e),
            "response": e.response.text if e.response else None
        }
        raise Exception(f"D-ID API Error: {json.dumps(error_details)}")

def check_talk_status(talk_id: str) -> str:
    """Check talk status with proper authentication"""
    headers = {"Authorization": f"Bearer {D_ID_API_KEY}"}
    
    for i in range(30):  # Check for 60 seconds max
        try:
            response = requests.get(
                f"{D_ID_BASE_URL}/talks/{talk_id}",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "done" and data.get("result_url"):
                return data["result_url"]
                
            print(f"Check #{i+1}: Status {data.get('status')}")
        except requests.exceptions.RequestException as e:
            print(f"Status check error: {str(e)}")
        
        time.sleep(2)
    
    raise Exception("Video generation timed out after 60 seconds")