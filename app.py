import os
import uuid
import traceback
import requests
from flask import Flask, request, send_file, Response, g
from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip, VideoFileClip

app = Flask(__name__)
API_KEY      = os.getenv('A2E_API_KEY')  # must be set in Render env
AVATAR_ID    = "68511a9dd4c7e25449f07b92"
API_BASE_URL = "https://video.a2e.ai"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        g.temp_files = []
        try:
            # ─── 1. Parse inputs ─────────────────────────────────────────
            prod = request.files.get('product_image')
            script = request.form.get('script')
            bg = request.files.get('background_image')
            bg_color = request.form.get('background_color', '#D3D3D3')

            print("📥 Received POST:")
            print("  script:", repr(script))
            print("  product_image:", prod.filename if prod else None)
            print("  background_image:", bg.filename if bg else None)
            print("  background_color:", bg_color)

            if not prod or not script:
                return "Error: missing product image or script", 400
            if not allowed_file(prod.filename) or (bg and not allowed_file(bg.filename)):
                return "Error: invalid file types", 400

            # ─── 2. Save uploads ────────────────────────────────────────
            os.makedirs('temp', exist_ok=True)
            prod_path = os.path.join('temp', f"{uuid.uuid4()}.{prod.filename.rsplit('.',1)[1]}")
            prod.save(prod_path); g.temp_files.append(prod_path)
            bg_path = None
            if bg:
                bg_path = os.path.join('temp', f"{uuid.uuid4()}.{bg.filename.rsplit('.',1)[1]}")
                bg.save(bg_path); g.temp_files.append(bg_path)

            # ─── 3. Call A2E.ai to generate video job ───────────────────
            headers = {
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json'
            }
            payload = {
                "title": "marketing clip",
                "anchor_id": AVATAR_ID,
                "text": script,
                "resolution": 1080,
                "voice_settings": {"language": "en-US", "speaker": "default"},
                "background": {"type": "color", "value": "rgba(255,255,255,1)"}
            }
            resp = requests.post(f"{API_BASE_URL}/api/v1/video/generate", headers=headers, json=payload)
            resp.raise_for_status()
            job_id = resp.json().get('job_id')
            if not job_id:
                raise RuntimeError("No job_id in response: " + resp.text)
            print("▶️ Job started:", job_id)

            # ─── 4. Poll for completion ────────────────────────────────
            video_url = None
            for _ in range(30):
                status = requests.get(f"{API_BASE_URL}/api/v1/job/{job_id}", headers=headers).json()
                s = status.get('status')
                print("   status:", s)
                if s == 'completed':
                    video_url = status['result']['video_url']
                    break
                if s in ('failed','cancelled'):
                    raise RuntimeError(f"Job {s}: " + status.get('error','no error msg'))
                import time; time.sleep(5)
            if not video_url:
                raise TimeoutError("Timed out waiting for video generation")

            # ─── 5. Download avatar video ───────────────────────────────
            av_path = os.path.join('temp', f"{uuid.uuid4()}.mp4")
            with requests.get(video_url, stream=True) as r:
                r.raise_for_status()
                with open(av_path,'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
            g.temp_files.append(av_path)
            print("⬇️ Downloaded avatar video to", av_path)

            # ─── 6. Composite with MoviePy ─────────────────────────────
            clip = VideoFileClip(av_path)
            duration = clip.duration
            size = (1080,1080)
            if bg_path:
                background = ImageClip(bg_path).set_duration(duration).resize(size)
            else:
                c = [int(bg_color[i:i+2],16) for i in (1,3,5)]
                background = ColorClip(size=size, color=c).set_duration(duration)
            avatar = clip.resize(width=size[0]//4).set_position(('left','bottom'))
            product = ImageClip(prod_path).set_duration(duration).resize(width=size[0]//2).set_position('center')
            final = CompositeVideoClip([background, product, avatar], size=size).set_audio(clip.audio)
            out_path = os.path.join('temp', f"{uuid.uuid4()}.mp4")
            final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac')
            g.temp_files.append(out_path)

            # ─── 7. Return resulting video ──────────────────────────────
            return send_file(out_path, mimetype='video/mp4', as_attachment=False,
                             download_name='marketing_video.mp4')

        except Exception as e:
            # Log full traceback
            print("❌ Exception during processing:")
            traceback.print_exc()
            # Return error to frontend so JS can show it
            return f"Error: {str(e)}", 500

        finally:
            # Clean up temp files on each request
            for fpath in getattr(g, 'temp_files', []):
                try: os.remove(fpath)
                except: pass

    # GET → serve index.html from same folder
    try:
        with open("index.html","r",encoding="utf-8") as f:
            return Response(f.read(), mimetype="text/html")
    except Exception as e:
        print("❌ Could not read index.html:")
        traceback.print_exc()
        return f"Error loading HTML: {str(e)}", 500

if __name__ == "__main__":
    # debug=True will also show errors in browser
    app.run(debug=True)
