import os
import requests
import time
import uuid
import json
import logging
from PIL import Image
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video-generator")

# Load environment variables
AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION")
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY").strip()  # Clean whitespace

# HeyGen API endpoints
HEYGEN_API_URL = "https://api.heygen.com/v1"

def preprocess_image(image_bytes):
    """Converts image to JPEG for compatibility"""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            rgb_image = img.convert("RGB")
            output_buffer = io.BytesIO()
            rgb_image.save(output_buffer, format="JPEG", quality=95)
            return output_buffer.getvalue()
    except Exception as e:
        logger.error(f"Image processing failed: {str(e)}")
        raise

def generate_azure_tts(script: str, voice: str = "en-US-AriaNeural") -> str:
    """Generate TTS audio and return public URL"""
    try:
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
    except Exception as e:
        logger.error(f"Azure TTS failed: {str(e)}")
        raise

def upload_to_tmpfiles(file_path: str) -> str:
    """Uploads file to temporary hosting with error handling"""
    try:
        # Use a more reliable temporary host
        with open(file_path, 'rb') as f:
            response = requests.post(
                'https://tmpfiles.org/api/v1/upload',
                files={'file': (os.path.basename(file_path), f)}
            )
        
        if response.status_code != 200:
            raise Exception(f"Upload failed: {response.status_code} {response.text}")
        
        return response.json()['data']['url']
    except Exception as e:
        logger.error(f"Audio upload failed: {str(e)}")
        raise
    finally:
        try:
            os.remove(file_path)
        except:
            pass

def create_did_talk(image_bytes, audio_url):
    """Create HeyGen video with custom avatar"""
    try:
        logger.info("Creating HeyGen avatar...")
        avatar_id = create_heygen_avatar(image_bytes)
        
        logger.info(f"Avatar created: {avatar_id}")
        logger.info("Generating video...")
        video_id = generate_heygen_video(avatar_id, audio_url)
        
        return video_id
    except Exception as e:
        logger.error(f"Video creation failed: {str(e)}")
        raise

def create_heygen_avatar(image_bytes):
    """Upload image to create custom avatar"""
    try:
        headers = {"X-Api-Key": HEYGEN_API_KEY}
        
        response = requests.post(
            f"{HEYGEN_API_URL}/avatars",
            headers=headers,
            files={"file": ("avatar.jpg", image_bytes, "image/jpeg")},
            timeout=10
        )
        
        logger.debug(f"Avatar API response: {response.status_code} {response.text}")
        
        if response.status_code != 200:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', error_msg)
            except:
                pass
            raise Exception(f"Avatar API error: {response.status_code} - {error_msg}")
        
        return response.json()["data"]["avatar_id"]
    except Exception as e:
        logger.error(f"Avatar creation failed: {str(e)}")
        raise

def generate_heygen_video(avatar_id, audio_url):
    """Generate video with custom avatar and audio"""
    try:
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
            "test": True,
            "aspect_ratio": "16:9"
        }
        
        logger.debug(f"Video payload: {json.dumps(payload)}")
        
        response = requests.post(
            f"{HEYGEN_API_URL}/video/generate",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        logger.debug(f"Video API response: {response.status_code} {response.text}")
        
        if response.status_code != 200:
            error_msg = response.text
            try:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', error_msg)
            except:
                pass
            raise Exception(f"Video API error: {response.status_code} - {error_msg}")
        
        return response.json()["data"]["video_id"]
    except Exception as e:
        logger.error(f"Video generation failed: {str(e)}")
        raise

def check_talk_status(video_id):
    """Check video status and return URL when ready"""
    try:
        headers = {"X-Api-Key": HEYGEN_API_KEY}
        
        for i in range(20):  # Check for 1 minute max
            response = requests.get(
                f"{HEYGEN_API_URL}/video_status?video_id={video_id}",
                headers=headers,
                timeout=5
            )
            
            logger.debug(f"Status check {i+1}: {response.status_code} {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                status = data["data"].get("status")
                
                if status == "completed":
                    return data["data"]["video_url"]
                
                if status == "failed":
                    error = data["data"].get("error", "Unknown error")
                    raise Exception(f"Video failed: {error}")
            
            time.sleep(3)
        
        raise Exception("Video generation timed out")
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise