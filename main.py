import os
import time
import requests
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image
import tempfile

# Set your HeyGen API key in Render Environment Variables
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")

app = FastAPI()


@app.post("/generate-video")
async def generate_video(product: str = Form(...), script: str = Form(...), file: UploadFile = File(...)):
    headers = {
        "Authorization": f"Bearer {HEYGEN_API_KEY}",
        "Content-Type": "application/json"
    }

    # Save and process uploaded image
    product_image_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    with open(product_image_path, "wb") as img_file:
        img_file.write(await file.read())

    # Resize and prepare background with avatar overlay
    bg = Image.new("RGB", (1920, 1080), color="white")
    product_img = Image.open(product_image_path).convert("RGBA")
    product_img.thumbnail((600, 600))
    bg.paste(product_img, (100, 240), product_img if product_img.mode == 'RGBA' else None)

    composite_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
    bg.save(composite_path)

    # Upload the composite image to an image hosting service (you must configure this)
    # Here we assume a dummy URL is returned for simplicity
    composite_image_url = upload_to_imgbb(composite_path)  # You must define this function or upload method

    # Use HeyGen API to create video with custom background
    avatar_id = "b48e1a5d5e3a44ef9ce89f324c088cbc"  # Replace with a real avatar ID from HeyGen

    create_payload = {
        "avatar_id": avatar_id,
        "script": {
            "type": "text",
            "input": script
        },
        "config": {
            "output_quality": "1080p",
            "background_image_url": composite_image_url  # Important: using generated composite background
        }
    }

    create_response = requests.post(
        "https://api.heygen.com/v1/videos",
        headers=headers,
        json=create_payload
    )

    if create_response.status_code != 200:
        return JSONResponse(status_code=500, content={"error": "Failed to create video", "details": create_response.json()})

    video_id = create_response.json().get("video_id")

    # Poll for video completion
    status_url = f"https://api.heygen.com/v1/videos/{video_id}"
    for _ in range(30):
        time.sleep(3)
        status_response = requests.get(status_url, headers=headers)
        if status_response.status_code != 200:
            continue

        status_data = status_response.json()
        if status_data.get("status") == "completed":
            video_url = status_data.get("video_url")
            break
    else:
        return JSONResponse(status_code=500, content={"error": "Video generation timed out"})

    # Download and serve the video
    video_response = requests.get(video_url)
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    with open(temp_path, "wb") as f:
        f.write(video_response.content)

    return FileResponse(temp_path, media_type="video/mp4", filename="marketing_video.mp4")
