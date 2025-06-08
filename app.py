from flask import Flask, jsonify, request, send_file, send_from_directory
import requests
import uuid
import os
import shutil
import time

app = Flask(__name__, static_folder='.', static_url_path='')

# Directory to store temporary images
TEMP_DIR = "temp_images"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Basic cleanup: Remove files older than 1 hour
def cleanup_temp_dir():
    current_time = time.time()
    for filename in os.listdir(TEMP_DIR):
        file_path = os.path.join(TEMP_DIR, filename)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > 3600:  # 1 hour
                os.remove(file_path)

@app.route('/')
def serve_frontend():
    return send_file('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    # Clean up old files before generating a new one
    cleanup_temp_dir()

    data = request.get_json()
    description = data.get('description', "A futuristic city skyline at sunset, with flying cars and neon holographic billboards, cyberpunk style")
    style_preset = data.get('style_preset', "neon-punk")
    aspect_ratio = data.get('aspect_ratio', "16:9")
    output_format = data.get('output_format', "png")
    seed = int(data.get('seed', 0))

    # External API to generate the image
    url = "https://aiart-zroo.onrender.com/api/generate"
    payload = {
        "video_description": description,
        "negative_prompt": "blurry, low quality, distorted faces, poor lighting",
        "style_preset": style_preset if style_preset != "none" else "",
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
        "seed": seed
    }

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            result = response.json()
            image_url = result['image_url']

            # Download the image from the URL
            image_response = requests.get(image_url)
            if image_response.status_code != 200:
                return jsonify({"success": False, "error": "Failed to download generated image"}), 500

            # Save the image temporarily
            filename = f"{uuid.uuid4()}.{output_format}"
            file_path = os.path.join(TEMP_DIR, filename)
            with open(file_path, 'wb') as f:
                f.write(image_response.content)

            return jsonify({
                "success": True,
                "image_url": image_url,
                "filename": filename
            })
        else:
            return jsonify({"success": False, "error": response.text}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/download/<filename>')
def download_image(filename):
    file_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File not found"}), 404

    return send_from_directory(TEMP_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        # Clean up the temp directory on shutdown
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)