from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from moviepy.editor import *
import requests
import os
from uuid import uuid4

app = FastAPI()

PLAYHT_API_KEY = "your_playht_api_key"
PLAYHT_USER_ID = "your_playht_user_id"

OUTPUT_DIR = "videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_voiceover(script_text):
    url = "https://play.ht/api/v2/tts"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": PLAYHT_API_KEY,
        "X-User-Id": PLAYHT_USER_ID
    }
    payload = {
        "voice": "en-US-JennyNeural",
        "content": [script_text],
        "speed": 1.0,
        "quality": "high"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        audio_url = response.json().get("audioUrl")
        if audio_url:
            audio_response = requests.get(audio_url)
            audio_path = f"audio_{uuid4().hex}.mp3"
            with open(audio_path, "wb") as f:
                f.write(audio_response.content)
            return audio_path
    return None


def create_video(product_image_path, voiceover_path, product_name):
    duration = AudioFileClip(voiceover_path).duration
    
    image_clip = ImageClip(product_image_path).set_duration(duration).resize(height=720)
    image_clip = image_clip.set_position("center")

    audio_clip = AudioFileClip(voiceover_path)

    text_clip = TextClip(product_name, fontsize=60, color='white', font='Arial-Bold')\
        .set_position(('center', 'bottom')).set_duration(duration).margin(bottom=30)

    final = CompositeVideoClip([image_clip, text_clip])
    final = final.set_audio(audio_clip)

    output_path = os.path.join(OUTPUT_DIR, f"video_{uuid4().hex}.mp4")
    final.write_videofile(output_path, fps=24)
    return output_path


@app.post("/generate-video")
async def generate_video(
    product: str = Form(...),
    script: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Save uploaded image
        image_path = f"temp_{uuid4().hex}_{file.filename}"
        with open(image_path, "wb") as f:
            f.write(await file.read())

        # Generate voiceover
        voiceover_path = generate_voiceover(script)
        if not voiceover_path:
            return JSONResponse(status_code=500, content={"error": "Voiceover generation failed"})

        # Create video
        video_path = create_video(image_path, voiceover_path, product)

        return FileResponse(video_path, media_type="video/mp4", filename=os.path.basename(video_path))

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
