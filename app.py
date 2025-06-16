import os
import uuid
import re
from flask import Flask, request, send_file, g, jsonify, send_from_directory
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, ColorClip, CompositeVideoClip

app = Flask(__name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/', methods=['POST'])
def generate_video():
    try:
        g.temp_files = []
        
        # Get form data
        product_image = request.files.get('product_image')
        script = request.form.get('script')
        background_image = request.files.get('background_image')
        background_color = request.form.get('background_color', '#D3D3D3')
        
        # Validate inputs
        if not product_image or not script:
            return jsonify({'error': 'Please upload a product image and enter a script.'}), 400
        
        if not allowed_file(product_image.filename):
            return jsonify({'error': 'Invalid product image format. Use PNG, JPG, or JPEG.'}), 400
        
        # Validate script length
        if len(script) > 500:
            return jsonify({'error': 'Script exceeds 500 character limit.'}), 400
        
        # Save product image
        extension = product_image.filename.rsplit('.', 1)[1].lower()
        product_filename = f"{uuid.uuid4()}.{extension}"
        product_image.save(product_filename)
        g.temp_files.append(product_filename)
        
        # Handle background
        bg_path = None
        if background_image and background_image.filename != '' and allowed_file(background_image.filename):
            extension = background_image.filename.rsplit('.', 1)[1].lower()
            bg_filename = f"{uuid.uuid4()}.{extension}"
            background_image.save(bg_filename)
            g.temp_files.append(bg_filename)
            bg_path = bg_filename
        
        # Generate voiceover
        audio_filename = f"{uuid.uuid4()}.mp3"
        tts = gTTS(text=script, lang='en')
        tts.save(audio_filename)
        g.temp_files.append(audio_filename)
        
        # Load audio
        audio = AudioFileClip(audio_filename)
        
        # Set video dimensions (square format for social media)
        video_size = (1080, 1080)
        
        # Create background
        if bg_path:
            background = ImageClip(bg_path).set_duration(audio.duration).resize(video_size)
        else:
            # Convert hex to RGB
            rgb_color = hex_to_rgb(background_color)
            background = ColorClip(size=video_size, color=rgb_color).set_duration(audio.duration)
        
        # Create product clip
        product = ImageClip(product_filename).set_duration(audio.duration)
        
        # Resize product to fit within video with padding
        max_size = min(video_size) * 0.8
        product = product.resize(width=max_size) if product.w > product.h else product.resize(height=max_size)
        product = product.set_position(('center', 'center'))
        
        # Composite video
        video = CompositeVideoClip([background, product], size=video_size).set_audio(audio)
        
        # Generate output filename
        output_filename = f"{uuid.uuid4()}.mp4"
        video.write_videofile(
            output_filename, 
            fps=24, 
            codec='libx264', 
            audio_codec='aac',
            threads=4,
            preset='medium',
            ffmpeg_params=['-crf', '23']
        )
        
        # Cleanup temporary files
        for file in g.temp_files:
            try:
                os.remove(file)
            except:
                pass
        
        # Return video URL for preview and download
        return jsonify({
            'video_url': f'/video/{output_filename}',
            'filename': output_filename
        })
    
    except Exception as e:
        # Cleanup any created files
        if 'g.temp_files' in g:
            for file in g.temp_files:
                try:
                    os.remove(file)
                except:
                    pass
        return jsonify({'error': str(e)}), 500

@app.route('/video/<filename>')
def serve_video(filename):
    # Security check to prevent path traversal
    if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\.mp4$', filename):
        return "Invalid filename", 400
    
    try:
        return send_file(filename, as_attachment=False, conditional=True)
    finally:
        # Schedule file deletion after serving
        try:
            os.remove(filename)
        except:
            pass

@app.after_request
def add_header(response):
    # Prevent caching of video files
    if request.path.startswith('/video/'):
        response.headers['Cache-Control'] = 'no-store, max-age=0'
    return response

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
