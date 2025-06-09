from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from generate_video import generate_ai_video
import shutil
import os

app = FastAPI()

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
    filename = os.path.join(UPLOAD_DIR, file.filename)
    with open(filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    output_url = generate_ai_video(image_path=filename, script_text=script)
    return JSONResponse({"video_url": output_url})
