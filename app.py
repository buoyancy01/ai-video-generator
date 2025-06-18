import os
import uuid
import requests
from flask import Flask, request, send_file, Response, g
from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip, VideoFileClip

app = Flask(__name__)

API_KEY = os.getenv('A2E_API_KEY')  # Set in Render or your env
AVATAR_ID = "68511a9dd4c7e25449f07b92"
API_BASE_URL = "https://api.a2e.ai"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(fn):
    return fn and '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        g.temp_files = []
        try:
            prod = request.files.get('product_image')
            script = request.form.get('script')
            bg = request.files.get('background_image')
            bg_color = request.form.get('background_color', '#D3D3D3')

            if not prod or not script or not allowed_file(prod.filename) or (bg and not allowed_file(bg.filename)):
                return "Please provide a valid script and image files (PNG/JPG).", 400

            os.makedirs('temp', exist_ok=True)
            ext = prod.filename.rsplit('.', 1)[1]
            prod_path = f"temp/{uuid.uuid4()}.{ext}"
            prod.save(prod_path); g.temp_files.append(prod_path)
            
            bg_path = None
            if bg:
                ext = bg.filename.rsplit('.', 1)[1]
                bg_path = f"temp/{uuid.uuid4()}.{ext}"
                bg.save(bg_path); g.temp_files.append(bg_path)

            payload = {
                "title": "marketing clip",
                "anchor_id": AVATAR_ID,
                "anchor_type": 0,
                "script": script,
                "resolution": 1080,
                "voice_settings": {"language": "en-US", "speaker": "default"},
                "background": {"type": "color", "value": "rgba(255,255,255,1)"}
            }
            resp = requests.post(f"{API_BASE_URL}/api/v1/video/generate",
                                 headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
                                 json=payload)
            if not resp.ok:
                return "Failed to start A2E.ai video generation.", 500
            
            data = resp.json()
            job_id = data.get('data', {}).get('job_id') or data.get('job_id')
            if not job_id:
                return "A2E.ai did not return a job ID.", 500

            video_url = None
            for _ in range(30):
                st = requests.get(f"{API_BASE_URL}/api/v1/job/{job_id}",
                                  headers={'Authorization': f'Bearer {API_KEY}'})
                st_json = st.json()
                status = st_json.get('status')
                if status == 'completed':
                    video_url = st_json.get('data', {}).get('video_url') or st_json.get('result', {}).get('video_url')
                    break
                if status in ('failed', 'cancelled'):
                    return "A2E.ai failed to generate the video.", 500
                time.sleep(5)

            if not video_url:
                return "Timed out waiting for video generation.", 504

            av_path = f"temp/{uuid.uuid4()}.mp4"
            dl = requests.get(video_url, stream=True)
            if not dl.ok:
                return "Failed to download video.", 500

            with open(av_path, 'wb') as f:
                for chunk in dl.iter_content(8192):
                    f.write(chunk)
            g.temp_files.append(av_path)

            clip = VideoFileClip(av_path)
            dur = clip.duration
            size = (1080, 1080)
            if bg_path:
                background = ImageClip(bg_path).set_duration(dur).resize(size)
            else:
                col = [int(bg_color[i:i+2], 16) for i in (1, 3, 5)]
                background = ColorClip(size=size, color=col).set_duration(dur)
            avatar_clip = clip.resize(width=size[0] // 4).set_position(('left', 'bottom'))
            product_clip = ImageClip(prod_path).set_duration(dur).resize(width=size[0] // 2).set_position('center')
            final = CompositeVideoClip([background, product_clip, avatar_clip], size=size).set_audio(clip.audio)
            
            out_path = f"temp/{uuid.uuid4()}.mp4"
            final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac')
            g.temp_files.append(out_path)

            return send_file(out_path, mimetype='video/mp4', as_attachment=False, download_name='marketing_video.mp4')

        except Exception:
            return "An internal error occurred. Please try again.", 500

        finally:
            for fpath in getattr(g, 'temp_files', []):
                try: os.remove(fpath)
                except: pass

    try:
        return Response(open('index.html', 'r', encoding='utf-8').read(), mimetype='text/html')
    except:
        return "Could not load page.", 500

if __name__ == '__main__':
    import time
    app.run(debug=False)
