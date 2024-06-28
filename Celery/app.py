from flask import Flask, request, jsonify
import os
from tasks import process_video_task

app = Flask(__name__)
UPLOAD_FOLDER = 'F:/Celery'
OUTPUT_FOLDER = 'F:/Celery_output'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        # Enqueue the video processing task
        process_video_task.delay(file_path, OUTPUT_FOLDER)
        return jsonify({'message': 'File uploaded successfully', 'file_path': file_path}), 201

if __name__ == '__main__':
    app.run(debug=True)