from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from generate_video import generate_tts, create_did_talk, check_talk_status

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate")
async def generate(file: UploadFile, script: str = Form(...)):
    try:
        image_bytes = await file.read()
        audio_url = await generate_tts(script)
        talk_id = await create_did_talk(image_bytes, audio_url)
        return {"talk_id": talk_id, "message": "Processing... Use /status/{talk_id} to check video status."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/status/{talk_id}")
async def status(talk_id: str):
    try:
        result_url = await check_talk_status(talk_id)
        if result_url:
            return {"status": "done", "video_url": result_url}
        return {"status": "processing"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
