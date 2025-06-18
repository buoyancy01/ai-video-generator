import os
import uuid
import traceback
import requests
from flask import Flask, request, send_file, Response, g
from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip, VideoFileClip

app = Flask(__name__)
API_KEY      = os.getenv('A2E_API_KEY')
AVATAR_ID    = "68511a9dd4c7e25449f07b92"
API_BASE_URL = "https://api.a2e.ai"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(fn):
    return fn and '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET','POST'])
def index():
    if request.method=='POST':
        g.temp_files = []
        try:
            # 1. Parse inputs
            prod = request.files.get('product_image')
            script = request.form.get('script')
            bg = request.files.get('background_image')
            bg_color = request.form.get('background_color','#D3D3D3')

            print("📥 Received POST:")
            print("  script:", repr(script))
            print("  product_image:", prod.filename if prod else None)
            print("  background_image:", bg.filename if bg else None)
            print("  background_color:", bg_color)

            if not prod or not script:
                return "Error: missing product image or script", 400
            if not allowed_file(prod.filename) or (bg and not allowed_file(bg.filename)):
                return "Error: invalid file types", 400

            # 2. Save uploads
            os.makedirs('temp',exist_ok=True)
            prod_ext = prod.filename.rsplit('.',1)[1]
            prod_path = f"temp/{uuid.uuid4()}.{prod_ext}"
            prod.save(prod_path); g.temp_files.append(prod_path)
            bg_path = None
            if bg:
                bg_ext = bg.filename.rsplit('.',1)[1]
                bg_path = f"temp/{uuid.uuid4()}.{bg_ext}"
                bg.save(bg_path); g.temp_files.append(bg_path)

            # 3. Initiate video generation
            gen_url = f"{API_BASE_URL}/api/v1/video/generate"
            headers = {'Authorization':f'Bearer {API_KEY}','Content-Type':'application/json'}
            payload = {
                "title": "marketing clip",
                "anchor_id": AVATAR_ID,
                "anchor_type": 0,
                "script": script,
                "resolution": 1080,
                "voice_settings": {"language": "en-US", "speaker": "default"},
                "background": {"type": "color", "value": "rgba(255,255,255,1)"}
            }
            resp = requests.post(gen_url, headers=headers, json=payload)
            print(f"🎯 A2E generate status: {resp.status_code}")
            print("📦 A2E response text:", resp.text)
            if not resp.ok:
                return f"Error from A2E.ai: {resp.status_code} {resp.text}", resp.status_code

            # 4. Parse JSON robustly
            try:
                data = resp.json()
            except Exception as e:
                print("❌ Failed to parse JSON from A2E.ai:", str(e))
                return f"Error parsing A2E response: {str(e)}", 500

            job_id = data.get('data', {}).get('job_id') or data.get('job_id')
            if not job_id:
                return f"Error: no job_id in A2E response: {resp.text}", 500
            print("▶️ Job started:", job_id)

            # 5. Poll for completion
            job_url = f"{API_BASE_URL}/api/v1/job/{job_id}"
            video_url = None
            for _ in range(30):
                st = requests.get(job_url, headers=headers)
                print(f"🔄 Poll status {st.status_code}: {st.text}")
                if not st.ok:
                    return f"Error polling job: {st.status_code} {st.text}", st.status_code
                st_json = st.json()
                status = st_json.get('status')
                if status == 'completed':
                    video_url = st_json.get('data', {}).get('video_url') or st_json.get('result', {}).get('video_url')
                    break
                if status in ('failed','cancelled'):
                    return f"A2E job {status}: {st_json.get('error', st.text)}", 500
                import time; time.sleep(5)
            if not video_url:
                return "Error: timed out waiting for video generation", 504

            # 6. Download avatar video
            av_path = f"temp/{uuid.uuid4()}.mp4"
            dl = requests.get(video_url, stream=True)
            if not dl.ok:
                return f"Error downloading video: {dl.status_code} {dl.text}", dl.status_code
            with open(av_path,'wb') as f:
                for c in dl.iter_content(8192): f.write(c)
            g.temp_files.append(av_path)
            print("⬇️ Downloaded avatar video to", av_path)

            # 7. Composite
            clip = VideoFileClip(av_path)
            dur = clip.duration; size = (1080,1080)
            if bg_path:
                bg_clip = ImageClip(bg_path).set_duration(dur).resize(size)
            else:
                col = [int(bg_color[i:i+2],16) for i in (1,3,5)]
                bg_clip = ColorClip(size=size, color=col).set_duration(dur)
            avatar_clip = clip.resize(width=size[0]//4).set_position(('left','bottom'))
            product_clip = ImageClip(prod_path).set_duration(dur).resize(width=size[0]//2).set_position('center')
            final = CompositeVideoClip([bg_clip, product_clip, avatar_clip], size=size).set_audio(clip.audio)
            out_path = f"temp/{uuid.uuid4()}.mp4"
            final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac')
            g.temp_files.append(out_path)

            return send_file(out_path, mimetype='video/mp4', as_attachment=False, download_name='marketing_video.mp4')

        except Exception as e:
            print("❌ Exception during processing:")
            traceback.print_exc()
            return f"Error: {str(e)}", 500

        finally:
            for fpath in getattr(g,'temp_files',[]):
                try: os.remove(fpath)
                except: pass

    # GET -> serve index.html
    try:
        html = open('index.html','r',encoding='utf-8').read()
        return Response(html, mimetype='text/html')
    except Exception as e:
        print("❌ Could not read index.html:")
        traceback.print_exc()
        return f"Error loading HTML: {str(e)}",500

if __name__=='__main__':
    app.run(debug=True)
