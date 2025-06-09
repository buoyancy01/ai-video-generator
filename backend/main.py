from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from generate_video import generate_ai_video # <--- FIXED: Removed the leading dot for absolute import
import shutil
import os

app = FastAPI()

# IMPORTANT: During development, allow_origins=["*"] is fine.
# For production, replace "*" with your Vercel frontend URL, e.g.,
# allow_origins=["https://your-frontend-name.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Will be updated for production later
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

    # Sanitize filename to prevent directory traversal issues
    filename = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))

    try:
        with open(filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    try:
        output_url = generate_ai_video(image_path=filename, script_text=script)
        if not output_url or "Error" in output_url: # Check for error string or None
            raise HTTPException(status_code=500, detail=output_url if output_url else "Video generation failed")
        return JSONResponse({"video_url": output_url})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation internal error: {e}: {e}")
    finally:
        # Clean up the uploaded file after processing
        if os.path.exists(filename):
            os.remove(filename)