from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# FIXED: Use relative import with full file path to avoid circular or incorrect import errors
from generate_video import generate_ai_video

import shutil
import os

app = FastAPI()

# Allow all CORS (update with your Vercel domain for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/generate")
async def generate(file: UploadFile, script: str = Form(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Sanitize filename
    filename = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))

    try:
        with open(filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        output_url = generate_ai_video(image_path=filename, script_text=script)
        if not output_url or "Error" in str(output_url):
            raise HTTPException(status_code=500, detail=output_url or "Video generation failed")
        return JSONResponse({"video_url": output_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation internal error: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)
