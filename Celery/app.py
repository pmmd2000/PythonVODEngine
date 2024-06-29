from flask import Flask, request, jsonify
import os
from tasks import process_video_task
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

upload_dest = str(os.getenv('UPLOAD_DEST'))
output_dest = str(os.getenv('OUTPUT_DEST'))

@app.route('/upload', methods=['POST']) # type: ignore
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        file_path = os.path.join(upload_dest, file.filename) # type: ignore
        file.save(file_path)
        process_video_task.delay(file_path, output_dest)
        return jsonify({'message': 'File uploaded successfully', 'file_path': file_path}), 201

if __name__ == '__main__':
    app.run(debug=True, host=os.getenv('HOST'))