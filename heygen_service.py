import os
import requests
import time
import uuid
from PIL import Image
import io

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_API_URL = "https://api.heygen.com/v1"

def create_heygen_avatar(image_bytes):
    """Upload image to create custom avatar"""
    headers = {"X-Api-Key": HEYGEN_API_KEY}
    
    # Convert to JPEG
    with Image.open(io.BytesIO(image_bytes)) as img:
        rgb_image = img.convert("RGB")
        output_buffer = io.BytesIO()
        rgb_image.save(output_buffer, format="JPEG")
        image_bytes = output_buffer.getvalue()
    
    # Upload image
    response = requests.post(
        f"{HEYGEN_API_URL}/avatars",
        headers=headers,
        files={"file": ("avatar.jpg", image_bytes, "image/jpeg")}
    )
    response.raise_for_status()
    return response.json()["data"]["avatar_id"]

def generate_heygen_video(avatar_id, audio_url):
    """Generate video with custom avatar and audio"""
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }
    
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
        "aspect_ratio": "16:9"
    }
    
    # Create video task
    response = requests.post(
        f"{HEYGEN_API_URL}/video/generate",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    return response.json()["data"]["video_id"]

def get_heygen_video_url(video_id):
    """Check video status"""
    headers = {"X-Api-Key": HEYGEN_API_KEY}
    
    for _ in range(30):  # Check for 60 seconds
        response = requests.get(
            f"{HEYGEN_API_URL}/video/{video_id}",
            headers=headers
        )
        data = response.json()
        
        if data["data"]["status"] == "completed":
            return data["data"]["video_url"]
        
        time.sleep(2)
    
    raise Exception("Video generation timed out")