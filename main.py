from fastapi import FastAPI, HTTPException
from generate_video import generate_ai_video

app = FastAPI()

@app.post("/generate")
async def generate(
    file: UploadFile = File(...),
    script: str = Form(...)
):
    try:
        video_url = await generate_ai_video(script, file)
        return {"video_url": video_url}
    except Exception as e:
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail=f"Video generation internal error: {str(e)}")
