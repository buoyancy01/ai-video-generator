from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from generate_video import generate_azure_tts, upload_to_tmpfiles, create_did_talk, check_talk_status

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
    raw_image = file.file.read()
    image_bytes = preprocess_image(raw_image)
    audio_path = generate_azure_tts(script)
    audio_url = upload_to_tmpfiles(audio_path)

    talk_id = create_did_talk(image_bytes, audio_url)
    video_url = check_talk_status(talk_id)

    return {"video_url": video_url}
@app.get("/status/{talk_id}")
async def status(talk_id: str):
    try:
        result_url = await check_talk_status(talk_id)
        if result_url:
            return {"status": "done", "video_url": result_url}
        return {"status": "processing"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
