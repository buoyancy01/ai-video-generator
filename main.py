from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse, RedirectResponse
import os
import json
import requests
from generate_video import generate_azure_tts, create_did_talk, check_talk_status, preprocess_image

app = FastAPI()

@app.post("/generate")
async def generate(file: UploadFile, script: str = Form(...)):
    try:
        raw_image = await file.read()
        image_bytes = preprocess_image(raw_image)

        audio_url = generate_azure_tts(script)
        talk_id = create_did_talk(image_bytes, audio_url)

        video_url = check_talk_status(talk_id)
        return {"video_url": video_url}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/verify")
async def verify_credentials():
    """Enhanced verification endpoint"""
    creds = {
        "D_ID_KEY_SET": bool(os.getenv("D_ID_API_KEY")),
        "D_ID_REGION": os.getenv("D_ID_REGION", "global"),
        "AZURE_KEY_SET": bool(os.getenv("AZURE_TTS_KEY")),
        "AZURE_REGION": os.getenv("AZURE_TTS_REGION", "NOT SET"),
        "RENDER_INSTANCE": os.getenv("RENDER_INSTANCE_ID", "LOCAL")
    }
    
    # Test D-ID authentication carefully
    try:
        headers = {"Authorization": f"Bearer {os.getenv('D_ID_API_KEY')}"}
        response = requests.get(f"{os.getenv('D_ID_BASE_URL', 'https://api.d-id.com')}/credentials", 
                               headers=headers,
                               timeout=5)
        creds["DID_AUTH_TEST"] = response.status_code == 200
        if creds["DID_AUTH_TEST"]:
            creds["DID_CREDITS"] = response.json().get("api_credits")
    except Exception as e:
        creds["DID_AUTH_TEST"] = False
        creds["DID_AUTH_ERROR"] = str(e)
    
    return creds

@app.get("/test")
async def test_endpoint():
    """Full test flow with sample data"""
    try:
        # Use a sample image from your project
        with open("sample_image.jpg", "rb") as f:
            image_bytes = preprocess_image(f.read())
        
        script = "This is a test of the video generation system. If you can see this video, it means everything is working correctly."
        audio_url = generate_azure_tts(script)
        talk_id = create_did_talk(image_bytes, audio_url)
        video_url = check_talk_status(talk_id)
        return RedirectResponse(url=video_url)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
        return JSONResponse(status_code=500, content={"error": str(e)})
        
