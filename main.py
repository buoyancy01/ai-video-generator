import os
import uuid
from flask import Flask, request, render_template, send_file, g
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, ColorClip, CompositeVideoClip

app = Flask(__name__, template_folder='.')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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

        # Save product image with unique name
        extension = product_image.filename.rsplit('.', 1)[1].lower()
        product_filename = str(uuid.uuid4()) + '.' + extension
        product_path = product_filename
        product_image.save(product_path)
        g.temp_files.append(product_path)

        # Handle background image
        bg_path = None
        if background_image and allowed_file(background_image.filename):
            extension = background_image.filename.rsplit('.', 1)[1].lower()
            bg_filename = str(uuid.uuid4()) + '.' + extension
            bg_path = bg_filename
            background_image.save(bg_path)
            g.temp_files.append(bg_path)

        # Generate voiceover
        audio_filename = str(uuid.uuid4()) + '.mp3'
        audio_path = audio_filename
        tts = gTTS(text=script, lang='en')
        tts.save(audio_path)
        g.temp_files.append(audio_path)

        # Load audio
        audio = AudioFileClip(audio_path)

        # Set video dimensions
        video_size = (1080, 1080)

        # Handle background
        if bg_path:
            background = ImageClip(bg_path).set_duration(audio.duration).resize(video_size)
        else:
            color = [int(background_color[1:3], 16), int(background_color[3:5], 16), int(background_color[5:7], 16)]
            background = ColorClip(size=video_size, color=color).set_duration(audio.duration)

        # Load and resize product image
        product = ImageClip(product_path).set_duration(audio.duration).resize(width=int(video_size[0] * 0.8))
        product = product.set_position(('center', 'center'))

        # Composite video
        video = CompositeVideoClip([background, product], size=video_size).set_audio(audio)
        output_filename = str(uuid.uuid4()) + '.mp4'
        output_path = output_filename
        video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac')
        g.temp_files.append(output_path)

        # Send file for download
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
