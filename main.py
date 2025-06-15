import os
import time
import requests
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image
import tempfile

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
        return JSONResponse(status_code=500, content={"error": f"Image upload failed: {str(e)}"})

    # Step 2: Generate video with HeyGen
    headers = {
        "Authorization": f"Bearer {HEYGEN_API_KEY}",
        "Content-Type": "application/json"
    }

    avatar_id = "b48e1a5d5e3a44ef9ce89f324c088cbc"  # Your custom uploaded avatar

    create_payload = {
        "avatar_id": avatar_id,
        "script": {
            "type": "text",
            "input": script
        },
        "config": {
            "output_quality": "1080p",
            "background_url": composite_url
        }
    }

    create_response = requests.post(
        "https://api.heygen.com/v1/videos",
        headers=headers,
        json=create_payload
    )

    if create_response.status_code != 200:
        # Attempt to parse JSON safely
details = None
try:
    details = create_response.json()
except Exception:
    details = create_response.text
return JSONResponse(status_code=500, content={"error": "Failed to create video", "details": details})

    video_id = create_response.json().get("video_id")
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

    video_response = requests.get(video_url)
    temp_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    with open(temp_video_path, "wb") as f:
        f.write(video_response.content)

    return FileResponse(temp_video_path, media_type="video/mp4", filename="marketing_video.mp4")
