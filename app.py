import os
import uuid
import traceback
import requests
from flask import Flask, request, send_file, Response, g
from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip, VideoFileClip

app = Flask(__name__)
API_KEY      = os.getenv('A2E_API_KEY')
AVATAR_ID    = "68511a9dd4c7e25449f07b92"
API_BASE_URL = "https://api.a2e.ai"   # <-- corrected!

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(fn):
    return '.' in fn and fn.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET','POST'])
def index():
    if request.method=='POST':
        g.temp_files = []
        try:
            # 1. parse
            prod = request.files.get('product_image')
            script = request.form.get('script')
            bg = request.files.get('background_image')
            bg_color = request.form.get('background_color','#D3D3D3')
            if not prod or not script:
                return "Error: missing product image or script", 400

            # 2. save uploads
            os.makedirs('temp',exist_ok=True)
            ext=prod.filename.rsplit('.',1)[1]
            prod_path=f"temp/{uuid.uuid4()}.{ext}"
            prod.save(prod_path); g.temp_files.append(prod_path)
            bg_path=None
            if bg:
                ext=bg.filename.rsplit('.',1)[1]
                bg_path=f"temp/{uuid.uuid4()}.{ext}"
                bg.save(bg_path); g.temp_files.append(bg_path)

            # 3. call A2E
            url=f"{API_BASE_URL}/api/v1/video/generate"
            headers={'Authorization':f'Bearer {API_KEY}','Content-Type':'application/json'}
            payload={
                "title":"marketing clip",
                "anchor_id":AVATAR_ID,
                "anchor_type":0,               # <-- added
                "script":script,               # <-- was "text"
                "resolution":1080,
                "voice_settings":{"language":"en-US","speaker":"default"},
                "background":{"type":"color","value":"rgba(255,255,255,1)"}
            }
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code!=200:
                # print the API's error message so you see exactly why it's 400
                print("📦 A2E.ai error response:", resp.text)
                resp.raise_for_status()
            job_id = resp.json().get('job_id')
            if not job_id:
                raise RuntimeError("no job_id in response: "+resp.text)

            # 4. poll
            video_url=None
            for _ in range(30):
                st = requests.get(f"{API_BASE_URL}/api/v1/job/{job_id}", headers=headers).json()
                if st['status']=='completed':
                    video_url=st['result']['video_url']
                    break
                if st['status'] in('failed','cancelled'):
                    raise RuntimeError(f"Job {st['status']}: "+st.get('error',''))
                import time; time.sleep(5)
            if not video_url:
                raise TimeoutError("timed out")

            # 5. download
            av_path=f"temp/{uuid.uuid4()}.mp4"
            with requests.get(video_url,stream=True) as r:
                r.raise_for_status()
                with open(av_path,'wb') as f:
                    for c in r.iter_content(8192):
                        f.write(c)
            g.temp_files.append(av_path)

            # 6. composite
            clip=VideoFileClip(av_path)
            dur=clip.duration; size=(1080,1080)
            if bg_path:
                background=ImageClip(bg_path).set_duration(dur).resize(size)
            else:
                c=[int(bg_color[i:i+2],16) for i in (1,3,5)]
                background=ColorClip(size=size,color=c).set_duration(dur)
            avatar=clip.resize(width=size[0]//4).set_position(('left','bottom'))
            product=ImageClip(prod_path).set_duration(dur).resize(width=size[0]//2).set_position('center')
            final=CompositeVideoClip([background,product,avatar],size=size).set_audio(clip.audio)
            out=f"temp/{uuid.uuid4()}.mp4"
            final.write_videofile(out,fps=24,codec='libx264',audio_codec='aac')
            g.temp_files.append(out)

            return send_file(out,mimetype='video/mp4',as_attachment=False,download_name='marketing_video.mp4')

        except Exception as e:
            print("❌ Exception during processing:")
            traceback.print_exc()
            return f"Error: {str(e)}", 500

        finally:
            for fpath in getattr(g,'temp_files',[]): 
                try: os.remove(fpath)
                except: pass

    # GET → serve index.html in same folder
    try:
        html=open("index.html","r",encoding="utf-8").read()
        return Response(html,mimetype="text/html")
    except Exception as e:
        print("❌ Could not read index.html:")
        traceback.print_exc()
        return f"Error loading HTML: {str(e)}",500

if __name__=="__main__":
    app.run(debug=True)
