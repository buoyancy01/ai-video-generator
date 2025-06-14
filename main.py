from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse, RedirectResponse
import os
import logging
from generate_video import generate_azure_tts, create_did_talk, check_talk_status, preprocess_image

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

@app.post("/generate")
async def generate(file: UploadFile, script: str = Form(...)):
    """Main endpoint for video generation"""
    try:
        logger.info(f"Starting generation for script: {script[:50]}...")
        
        raw_image = await file.read()
        logger.info(f"Received image: {len(raw_image)} bytes")
        
        image_bytes = preprocess_image(raw_image)
        logger.info("Image preprocessed")
        
        audio_url = generate_azure_tts(script)
        logger.info(f"Audio generated: {audio_url}")
        
        video_id = create_did_talk(image_bytes, audio_url)
        logger.info(f"Video task created: {video_id}")
        
        video_url = check_talk_status(video_id)
        logger.info(f"Video ready: {video_url}")
        
        return {"video_url": video_url}
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "type": type(e).__name__}
        )

@app.post("/generate_test")
async def generate_test(script: str = Form(...)):
    """Test endpoint with sample image"""
    try:
        logger.info(f"Test generation: {script[:50]}...")
        
        # Use a built-in sample image
        with open("sample_image.jpg", "rb") as f:
            image_bytes = preprocess_image(f.read())
        
        audio_url = generate_azure_tts(script)
        video_id = create_did_talk(image_bytes, audio_url)
        video_url = check_talk_status(video_id)
        
        return RedirectResponse(url=video_url)
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "type": type(e).__name__}
        )

@app.get("/verify")
async def verify_credentials():
    """Verify API credentials with detailed diagnostics"""
    try:
        creds = {
            "HEYGEN_KEY": bool(HEYGEN_API_KEY),
            "HEYGEN_KEY_LENGTH": len(HEYGEN_API_KEY) if HEYGEN_API_KEY else 0,
            "AZURE_KEY_SET": bool(os.getenv("AZURE_TTS_KEY")),
            "AZURE_REGION": os.getenv("AZURE_TTS_REGION", "NOT SET"),
        }
        
        # Test HeyGen authentication
        headers = {"X-Api-Key": HEYGEN_API_KEY}
        response = requests.get(
            "https://api.heygen.com/v1/account",
            headers=headers,
            timeout=5
        )
        
        creds["HEYGEN_STATUS"] = response.status_code
        if response.status_code == 200:
            creds["HEYGEN_CREDITS"] = response.json().get("data", {}).get("credits")
        else:
            creds["HEYGEN_RESPONSE"] = response.text[:200] + "..." if response.text else "Empty response"
            
        return creds
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def health_check():
    return {"status": "active", "service": "AI Video Generator"}