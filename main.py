from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse, RedirectResponse
import os
import requests
from generate_video import generate_azure_tts, create_did_talk, check_talk_status, preprocess_image
import uuid

app = FastAPI()

@app.post("/generate")
async def generate(file: UploadFile, script: str = Form(...)):
    """Main endpoint for video generation"""
    try:
        raw_image = await file.read()
        image_bytes = preprocess_image(raw_image)

        audio_url = generate_azure_tts(script)
        video_id = create_did_talk(image_bytes, audio_url)
        video_url = check_talk_status(video_id)
        
        return {"video_url": video_url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/generate_test")
async def generate_test(script: str = Form(...)):
    """Test endpoint with sample image"""
    try:
        # Use a built-in sample image
        with open("sample_image.jpg", "rb") as f:
            image_bytes = preprocess_image(f.read())
        
        audio_url = generate_azure_tts(script)
        video_id = create_did_talk(image_bytes, audio_url)
        video_url = check_talk_status(video_id)
        
        return RedirectResponse(url=video_url)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/verify")
async def verify_credentials():
    """Verify API credentials and service status"""
    creds = {
        "HEYGEN_KEY_SET": bool(os.getenv("HEYGEN_API_KEY")),
        "AZURE_KEY_SET": bool(os.getenv("AZURE_TTS_KEY")),
        "AZURE_REGION": os.getenv("AZURE_TTS_REGION", "NOT SET"),
        "RENDER_INSTANCE": os.getenv("RENDER_INSTANCE_ID", "LOCAL")
    }
    
    # Test HeyGen authentication
    try:
        headers = {"X-Api-Key": os.getenv("HEYGEN_API_KEY", "")}
        response = requests.get(
            "https://api.heygen.com/v1/account",
            headers=headers,
            timeout=5
        )
        creds["HEYGEN_AUTH_TEST"] = response.status_code == 200
        if creds["HEYGEN_AUTH_TEST"]:
            creds["HEYGEN_CREDITS"] = response.json().get("data", {}).get("credits")
    except Exception as e:
        creds["HEYGEN_AUTH_TEST"] = False
        creds["HEYGEN_AUTH_ERROR"] = str(e)
    
    return creds

@app.get("/")
async def health_check():
    """Service health endpoint"""
    return {"status": "active", "service": "AI Video Generator"}