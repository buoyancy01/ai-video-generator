import os
import requests
import base64
import time
import uuid
from PIL import Image
import io


AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION")
D_ID_API_KEY = os.getenv("D_ID_API_KEY")

def preprocess_image(image_bytes):
    """
    Converts any image (e.g. PNG with transparency) to JPEG to ensure D-ID compatibility.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        rgb_image = img.convert("RGB")  # Convert RGBA/others to RGB
        output_buffer = io.BytesIO()
        rgb_image.save(output_buffer, format="JPEG")
        return output_buffer.getvalue()


def generate_azure_tts(script: str, voice: str = "en-US-AriaNeural") -> str:
    # Generate audio using Azure TTS and return a temporary audio file path
    token_url = f"https://{AZURE_TTS_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
        "Content-Length": "0"
    }
    token_response = requests.post(token_url, headers=headers)
    if token_response.status_code != 200:
        raise Exception(f"Azure token error: {token_response.text}")
    
    access_token = token_response.text

    tts_url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    tts_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-32kbitrate-mono-mp3"
    }

    ssml = f"""
    <speak version='1.0' xml:lang='en-US'>
        <voice xml:lang='en-US' name='{voice}'>{script}</voice>
    </speak>
    """

    response = requests.post(tts_url, headers=tts_headers, data=ssml.encode('utf-8'))
    if response.status_code != 200:
        raise Exception(f"Azure TTS error: {response.text}")

    filename = f"audio_{uuid.uuid4().hex}.mp3"
    with open(filename, "wb") as f:
        f.write(response.content)

    return filename


def upload_to_tmpfiles(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        response = requests.post('https://tmpfiles.org/api/v1/upload', files=files)
        if response.status_code != 200:
            raise Exception("Failed to upload audio to tmpfiles")
        return response.json()['data']['url']


def create_did_talk(image_bytes, audio_url):
    """
    Sends the image and audio to D-ID to create a talking video.
    """
    headers = {
        "Authorization": f"Bearer {os.getenv('D_ID_API_KEY')}"
    }

    # Preprocess image to ensure JPEG format
    jpeg_bytes = preprocess_image(image_bytes)

    files = {
        "source_image": ("image.jpg", jpeg_bytes, "image/jpeg")
    }

    data = {
        "script": {
            "type": "audio",
            "audio_url": audio_url
        }
    }

    response = requests.post(
        "https://api.d-id.com/talks",
        headers=headers,
        files=files,
        data={"script": json.dumps(data["script"])}
    )

    if response.status_code != 200:
        raise Exception(f"D-ID error: {response.json()}")

    return response.json()["id"]



def check_talk_status(talk_id: str) -> str:
    headers = {
        "Authorization": f"Basic {D_ID_API_KEY}"
    }

    for _ in range(30):
        response = requests.get(f"https://api.d-id.com/talks/{talk_id}", headers=headers)
        data = response.json()
        if response.status_code != 200:
            raise Exception(f"D-ID status check failed: {data}")
        result_url = data.get("result_url")
        if result_url:
            return result_url
        time.sleep(2)

    raise Exception("Video generation timed out")
