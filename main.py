from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
import os
from generate_video import generate_tts, create_did_talk, check_talk_status, preprocess_image

app = FastAPI()

@app.post("/generate")
async def generate(file: UploadFile, script: str = Form(...)):
    try:
        raw_image = await file.read()
        image_bytes = preprocess_image(raw_image)  # Ensure compatibility with D-ID (JPEG format, etc.)

        audio_url = generate_tts(script)
        talk_id = create_did_talk(image_bytes, audio_url)

        video_url = check_talk_status(talk_id)
        return {"video_url": video_url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
