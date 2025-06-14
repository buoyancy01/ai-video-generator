import os
import time
import requests
import tempfile
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from PIL import Image, ImageDraw
from io import BytesIO

# Set your HeyGen API key in Render Environment Variables
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")  # You must set this in your Render environment variables

app = FastAPI()

def create_background_with_product(product_image_bytes):
    background = Image.new("RGB", (1920, 1080), (255, 255, 255))  # White background
    product_image = Image.open(BytesIO(product_image_bytes)).convert("RGBA")

    # Resize product image proportionally to fit nicely on the background
    product_image.thumbnail((800, 800))
    px, py = (int((1920 - product_image.width) / 2), int((1080 - product_image.height) / 2))
    background.paste(product_image, (px, py), product_image)

    # Save the result to bytes
    output = BytesIO()
    background.save(output, format="PNG")
    output.seek(0)
    return output

def upload_to_imgbb(image_bytes):
    url = "https://api.imgbb.com/1/upload"
    files = {'image': image_bytes.read()}
    response = requests.post(url, params={"key": IMGBB_API_KEY}, files=files)
    if response.status_code == 200:
        return response.json()["data"]["url"]
    else:
        raise Exception("Image upload failed")

@app.post("/generate-video")
async def generate_video(
    product: str = Form(...),
    script: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Step 1: Create background image with product
        image_bytes = await file.read()
        composite = create_background_with_product(image_bytes)

        # Step 2: Upload image to ImgBB
        background_url = upload_to_imgbb(composite)

        headers = {
            "Authorization": f"Bearer {HEYGEN_API_KEY}",
            "Content-Type": "application/json"
        }

        avatar_id = "b48e1a5d5e3a44ef9ce89f324c088cbc"  # Your uploaded HeyGen avatar ID

        # Step 3: Request HeyGen to create video
        create_payload = {
            "avatar_id": avatar_id,
            "script": {
                "type": "text",
                "input": script
            },
            "config": {
                "output_quality": "1080p",
                "background": "green",
                "background_url": background_url
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

        # Step 4: Poll video status
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

        # Step 5: Download and return video
        video_response = requests.get(video_url)
        temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        with open(temp_path, "wb") as f:
            f.write(video_response.content)

        return FileResponse(temp_path, media_type="video/mp4", filename="marketing_video.mp4")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
