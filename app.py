import os
import uuid
import requests
from flask import Flask, request, render_template, send_file, g
from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip, VideoFileClip

app = Flask(__name__, template_folder='.')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

API_KEY = os.getenv('A2E_API_KEY')  # Securely stored in Render environment variables
AVATAR_ID = "68511a9dd4c7e25449f07b92"  # Chosen default en-US avatar
API_URL = "https://video.a2e.ai"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        g.temp_files = []

        product_image = request.files.get('product_image')
        script = request.form.get('script')
        background_image = request.files.get('background_image')
        background_color = request.form.get('background_color', '#D3D3D3')

        if not product_image or not script:
            return "Please upload a product image and enter a script.", 400
        if not allowed_file(product_image.filename):
            return "Invalid product image format. Use PNG, JPG, or JPEG.", 400

        # Save product image
        ext = product_image.filename.rsplit('.', 1)[1].lower()
        product_path = f"{uuid.uuid4()}.{ext}"
        product_image.save(product_path)
        g.temp_files.append(product_path)

        # Handle background image
        bg_path = None
        if background_image and allowed_file(background_image.filename):
            ext = background_image.filename.rsplit('.', 1)[1].lower()
            bg_path = f"{uuid.uuid4()}.{ext}"
            background_image.save(bg_path)
            g.temp_files.append(bg_path)

        # Generate avatar video with A2E.ai
        headers = {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        }
        payload = {
            "title": "marketing clip",
            "anchor_id": AVATAR_ID,
            "text": script,
            "resolution": 1080,
            "voice_settings": {
                "language": "en-US",
                "speaker": "default"
            },
            "background": {
                "type": "color",
                "value": "rgba(255,255,255,1)"
            }
        }

        try:
            generate_url = f"{API_URL}/api/v1/video/generate"
            resp = requests.post(generate_url, headers=headers, json=payload)
            resp.raise_for_status()
            job_id = resp.json()["job_id"]
        except Exception as e:
            return f"Error starting video job: {str(e)}", 500

        # Poll for job completion
        video_url = None
        try:
            status_url = f"{API_URL}/api/v1/job/{job_id}"
            for _ in range(30):
                status_resp = requests.get(status_url, headers=headers)
                status_data = status_resp.json()
                if status_data['status'] == 'completed':
                    video_url = status_data['result']['video_url']
                    break
                elif status_data['status'] in ('failed', 'cancelled'):
                    return f"Video generation failed: {status_data.get('error', 'Unknown error')}", 500
                import time
                time.sleep(10)
        except Exception as e:
            return f"Job check error: {str(e)}", 500

        if not video_url:
            return "Timed out waiting for video generation.", 504

        # Download the avatar video
        avatar_video_path = f"{uuid.uuid4()}.mp4"
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(avatar_video_path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        g.temp_files.append(avatar_video_path)

        # Load avatar video
        avatar_clip = VideoFileClip(avatar_video_path)
        video_size = (1080, 1080)

        # Background clip
        if bg_path:
            background = ImageClip(bg_path).set_duration(avatar_clip.duration).resize(video_size)
        else:
            color = [int(background_color[1:3], 16), int(background_color[3:5], 16), int(background_color[5:7], 16)]
            background = ColorClip(size=video_size, color=color).set_duration(avatar_clip.duration)

        # Position avatar video
        avatar_clip = avatar_clip.resize(width=video_size[0]//4).set_position(('left', 'bottom'))

        # Product image clip
        product_clip = ImageClip(product_path).set_duration(avatar_clip.duration).resize(width=video_size[0]//2).set_position('center')

        # Final composite
        final_clip = CompositeVideoClip([background, product_clip, avatar_clip], size=video_size).set_audio(avatar_clip.audio)
        output_path = f"{uuid.uuid4()}.mp4"
        final_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
        g.temp_files.append(output_path)

        return send_file(output_path, as_attachment=True, download_name='marketing_video.mp4')

    return render_template('index.html')


@app.after_request
def cleanup(response):
    if hasattr(g, 'temp_files'):
        for file in g.temp_files:
            try:
                os.remove(file)
            except:
                pass
    return response


if __name__ == '__main__':
    app.run(debug=True)
