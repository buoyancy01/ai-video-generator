import os
import time
import requests
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image
import tempfile
import uuid
import base64
from io import BytesIO

# ENV VARS: D-ID_API_KEY and IMGBB_API_KEY
DID_API_KEY = os.getenv("DID_API_KEY")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")

app = FastAPI()

def merge_with_white_background(uploaded_file: UploadFile) -> str:
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    temp_input.write(uploaded_file.file.read())
    temp_input.close()

    product_image = Image.open(temp_input.name).convert("RGBA")
    bg = Image.new("RGBA", (1920, 1080), "white")
    
    # Resize product image to fit nicely in frame
    max_width, max_height = 1000, 800
    product_image.thumbnail((max_width, max_height))

    x = (bg.width - product_image.width) // 2
    y = (bg.height - product_image.height) // 2
    bg.paste(product_image, (x, y), product_image)

    merged_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    bg.convert("RGB").save(merged_path, format="PNG")
    return merged_path

def upload_to_imgbb(image_path: str) -> str:
    with open(image_path, "rb") as f:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": IMGBB_API_KEY},
            files={"image": f}
        )
    response.raise_for_status()
    return response.json()["data"]["url"]

def create_did_presentation(script: str, image_url: str) -> str:
    """Create a D-ID presentation and return the presentation ID"""
    headers = {
        "Authorization": f"Basic {base64.b64encode(f':{DID_API_KEY}'.encode()).decode()}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "script": {
            "type": "text",
            "input": script,
            "provider": {
                "type": "microsoft",
                "voice_id": "en-US-JennyNeural"
            }
        },
        "config": {
            "result_format": "mp4"
        },
        "source_url": image_url,
        "webhook": ""  # Not needed for immediate sync
    }
    
    response = requests.post(
        "https://api.d-id.com/talks",
        headers=headers,
        json=payload
    )
    
    if response.status_code != 201:
        raise Exception(f"D-ID API error: {response.status_code} - {response.text}")
    
    return response.json()["id"]

def get_did_video_url(presentation_id: str) -> str:
    """Get video URL from D-ID presentation"""
    headers = {
        "Authorization": f"Basic {base64.b64encode(f':{DID_API_KEY}'.encode()).decode()}"
    }
    
    for _ in range(30):  # 30 attempts * 3 seconds = 90 seconds timeout
        time.sleep(3)
        response = requests.get(
            f"https://api.d-id.com/talks/{presentation_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            continue
            
        data = response.json()
        status = data.get("status")
        
        if status == "done":
            return data["result_url"]
        elif status == "error":
            raise Exception("D-ID video generation failed")
    
    raise Exception("D-ID video generation timed out")

@app.post("/generate-video")
async def generate_video(
    product: str = Form(...),
    script: str = Form(...),
    file: UploadFile = File(...)
):
    # Step 1: Merge product image with white background
    composite_path = merge_with_white_background(file)
    try:
        composite_url = upload_to_imgbb(composite_path)
    except Exception as e:
        if os.path.exists(composite_path):
            os.remove(composite_path)
        return JSONResponse(status_code=500, content={"error": f"Image upload failed: {str(e)}"})
    finally:
        if os.path.exists(composite_path):
            os.remove(composite_path)

    # Step 2: Generate video with D-ID
    try:
        presentation_id = create_did_presentation(script, composite_url)
        video_url = get_did_video_url(presentation_id)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Video generation failed: {str(e)}"}
        )

    # Step 3: Serve the generated video
    try:
        video_response = requests.get(video_url, stream=True)
        video_response.raise_for_status()
        
        # Stream video directly to client
        return FileResponse(
            BytesIO(video_response.content),
            media_type="video/mp4",
            filename=f"{product.replace(' ', '_')}_video.mp4"
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to download video: {str(e)}"}
        )
