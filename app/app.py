from logging import exception
from types import NoneType
from flask import Flask, request, jsonify
import os
from tasks import process_video_task
from dotenv import load_dotenv
import db_connections
import Conversion
import functions

load_dotenv()
app = Flask(__name__)

ConvertedVideos_path = str(os.getenv('CONVERTED_VIDEOS_PATH'))
OriginalVideos_path= str(os.getenv('ORIGINAL_VIDEOS_PATH'))
VideoPkField = str(os.getenv("DB_VIDEOPK_FIELD"))


@app.route('/api/getVideoID',methods=['GET']) 
def video_details():
    response = db_connections.mssql_select_video(request.json['VideoName']) 
    response={VideoPkField: response[VideoPkField]} 
    return response,200 

@app.route('/api/startVideoConversion',methods=['POST']) 
def video_insert():
    RawVideoName=request.json['VideoName'] 
    VideoName=functions.RawVideoNameCheck(RawVideoName)
    VideoID= db_connections.mssql_select_video(VideoName)
    ConvertedVideo_path=os.path.join(ConvertedVideos_path,VideoName)
    if type(VideoID)==NoneType and not os.path.exists(ConvertedVideo_path):
        VideoData=db_connections.mssql_insert_video(VideoName)
        Conversion.ConvertVideo(VideoName,OriginalVideos_path,ConvertedVideos_path,VideoData)
        return 'Success',200
    elif os.path.exists(ConvertedVideo_path):
        raise Exception("Video directory already present")
    else:
        return 'Video already present',406

# @app.route('/api/upload', methods=['POST']) 
# def upload_video():
#     file = request.files['file']
#     if 'file' not in request.files:
#         return jsonify({'error': 'No file part'}), 400
#     if file.filename == '':
#         return jsonify({'error': 'No selected file'}), 400
#     if file:
#         OriginalVideo_path = os.path.join(OriginalVideos_path, file.filename) 
#         file.save(OriginalVideo_path)
#         process_video_task.delay(OriginalVideo_path, ConvertedVideos_path)
#         return jsonify({'message': 'File uploaded successfully', 'OriginalVideo_path': OriginalVideo_path}), 201

if __name__ == '__main__':
    app.run(debug=True, host=os.getenv('HOST'))