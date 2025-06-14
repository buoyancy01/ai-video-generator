import os
import requests
import time
import uuid
from PIL import Image
import io

# Load environment variables
AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

# HeyGen API endpoints
HEYGEN_API_URL = "https://api.heygen.com/v1"

def preprocess_image(image_bytes):
    """Converts image to JPEG for compatibility"""
    with Image.open(io.BytesIO(image_bytes)) as img:
        rgb_image = img.convert("RGB")
        output_buffer = io.BytesIO()
        rgb_image.save(output_buffer, format="JPEG", quality=95)
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
        # Use file.io for reliable hosting
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
    """Create HeyGen video with custom avatar"""
    # Step 1: Create avatar from image
    avatar_id = create_heygen_avatar(image_bytes)
    
    # Step 2: Generate video with avatar and audio
    video_id = generate_heygen_video(avatar_id, audio_url)
    
    return video_id

def create_heygen_avatar(image_bytes):
    """Upload image to create custom avatar"""
    headers = {"X-Api-Key": HEYGEN_API_KEY}
    
    # Send image to HeyGen
    response = requests.post(
        f"{HEYGEN_API_URL}/avatars",
        headers=headers,
        files={"file": ("avatar.jpg", image_bytes, "image/jpeg")}
    )
    
    # Handle errors
    if response.status_code != 200:
        error_msg = response.json().get('error', {}).get('message', 'Unknown error')
        raise Exception(f"HeyGen avatar creation failed: {error_msg}")
    
    return response.json()["data"]["avatar_id"]

def generate_heygen_video(avatar_id, audio_url):
    """Generate video with custom avatar and audio"""
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Video generation parameters
    payload = {
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": "normal"
            },
            "voice": {
                "type": "audio",
                "audio_url": audio_url
            },
            "background": {
                "type": "color",
                "value": "#FFFFFF"
            }
        }],
        "test": True,  # Use free test mode
        "aspect_ratio": "16:9",
        "caption": False
    }
    
    # Start video generation
    response = requests.post(
        f"{HEYGEN_API_URL}/video/generate",
        headers=headers,
        json=payload
    )
    
    # Handle errors
    if response.status_code != 200:
        error_msg = response.json().get('error', {}).get('message', 'Unknown error')
        raise Exception(f"HeyGen video creation failed: {error_msg}")
    
    return response.json()["data"]["video_id"]

def check_talk_status(video_id):
    """Check video status and return URL when ready"""
    headers = {"X-Api-Key": HEYGEN_API_KEY}
    
    # Check status periodically (max 2 minutes)
    for i in range(30):
        response = requests.get(
            f"{HEYGEN_API_URL}/video_status?video_id={video_id}",
            headers=headers
        )
        
        # Handle errors
        if response.status_code != 200:
            time.sleep(2)
            continue
        
        data = response.json()
        status = data["data"].get("status")
        
        # Return URL when ready
        if status == "completed":
            return data["data"]["video_url"]
        
        # Handle failures
        if status == "failed":
            error = data["data"].get("error", "Unknown error")
            raise Exception(f"Video generation failed: {error}")
        
        # Log progress
        print(f"Video status: {status} (check {i+1}/30)")
        time.sleep(4)
    
    raise Exception("Video generation timed out after 2 minutes")