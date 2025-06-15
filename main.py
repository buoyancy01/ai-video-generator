import os
import time
import requests
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image
import tempfile
import io

# ENV VARS: HEYGEN_API_KEY and IMGBB_API_KEY
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
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

    # Step 2: Generate video with HeyGen v2 API - FIXED VOICE SETTINGS
    headers = {
        "Authorization": f"Bearer {HEYGEN_API_KEY}",
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    }

    # CORRECTED PAYLOAD WITH PROPER VOICE SETTINGS
    create_payload = {
        "video_inputs": [{
            "type": "avatar",
            "avatar_id": "b48e1a5d5e3a44ef9ce89f324c088cbc",
            "avatar_style": "normal",
            "background": composite_url,
            "voice": {
                "type": "text",
                "input": script,
                "voice_settings": {
                    "voice_id": "en-US-JennyNeural"  # MOVED TO CORRECT LOCATION
                }
            }
        }],
        "ratio": "16:9",
        "test": False,
        "version": "v2"
    }

    create_response = requests.post(
        "https://api.heygen.com/v2/video/generate",
        headers=headers,
        json=create_payload
    )

    if create_response.status_code != 200:
        try:
            details = create_response.json()
        except Exception:
            details = create_response.text
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to create video",
                "details": details,
                "api_endpoint": "https://api.heygen.com/v2/video/generate",
                "status_code": create_response.status_code
            }
        )

    # Parse v2 response format
    response_data = create_response.json()
    video_id = response_data.get("data", {}).get("video_id")
    if not video_id:
        return JSONResponse(
            status_code=500,
            content={"error": "Video ID not found in response", "details": response_data}
        )

    # UPDATED v2 STATUS ENDPOINT
    status_url = f"https://api.heygen.com/v2/video/generate/status?video_id={video_id}"
    
    video_url = None
    for i in range(30):  # 30 attempts * 3 seconds = 90 seconds timeout
        time.sleep(3)
        status_response = requests.get(status_url, headers=headers)
        
        if status_response.status_code != 200:
            print(f"Status check failed ({i+1}/30): {status_response.status_code} - {status_response.text}")
            continue

        status_data = status_response.json()
        video_status = status_data.get("data", {}).get("status")
        
        if video_status == "completed":
            video_url = status_data.get("data", {}).get("video_url")
            break
        elif video_status == "failed":
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Video generation failed",
                    "details": status_data.get("data", {})
                }
            )
        
        print(f"Status ({i+1}/30): {video_status}")

    if not video_url:
        return JSONResponse(
            status_code=500,
            content={"error": "Video generation timed out after 90 seconds"}
        )

    # Step 3: Serve the generated video
    temp_video_path = None
    try:
        video_response = requests.get(video_url, stream=True)
        video_response.raise_for_status()

        temp_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        with open(temp_video_path, "wb") as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return FileResponse(
            temp_video_path,
            media_type="video/mp4",
            filename=f"{product.replace(' ', '_')}_video.mp4"
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to download video: {str(e)}"}
        )
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            os.remove(temp_video_path)
