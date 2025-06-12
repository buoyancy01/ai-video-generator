from fastapi import FastAPI, HTTPException
from generate_video import generate_ai_video

app = FastAPI()

@app.post("/generate")
def create_video(payload: dict):
    try:
        script = payload.get("script", "")
        if not script:
            raise HTTPException(status_code=400, detail="Missing script")

        video_url = generate_ai_video(script)
        return {"video_url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation internal error: {str(e)}")
