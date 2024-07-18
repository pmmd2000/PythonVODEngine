from types import NoneType
from flask import Flask, request
import os
from dotenv import load_dotenv
import db_connections
import Conversion
import functions
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_cors import CORS

app = Flask(__name__)
load_dotenv()

CORS(app, resources={r"/*": {"origins": os.getenv('CORS_ORIGIN_DOMAIN')}}, supports_credentials=True)

ConvertedVideos_path = str(os.getenv('CONVERTED_VIDEOS_PATH'))
OriginalVideos_path= str(os.getenv('ORIGINAL_VIDEOS_PATH'))
VideoPkField = str(os.getenv("DB_VIDEOPK_FIELD"))
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)


@app.route('/api/startVideoConversion',methods=['POST']) 
@jwt_required()
def video_insert():
    RawVideoName=request.json['VideoName'] 
    VideoName=functions.RawVideoNameCheck(RawVideoName)['VideoName']
    Extension=functions.RawVideoNameCheck(RawVideoName)['Extension']
    VideoID= db_connections.mssql_select_video(VideoName)
    ConvertedVideo_path=os.path.join(ConvertedVideos_path,VideoName)
    Duration=Conversion.get_video_duration(VideoName,Extension,OriginalVideos_path)
    if type(VideoID)==NoneType and not os.path.exists(ConvertedVideo_path):
        VideoData=db_connections.mssql_insert_video(VideoName,Extension,float(Duration))
        Conversion.ConvertVideo(VideoName,OriginalVideos_path,ConvertedVideos_path,VideoData)
        return 'Success',200
    elif os.path.exists(ConvertedVideo_path):
        raise Exception("Video directory already present")
    else:
        return 'Video already present',406

if __name__ == '__main__':
    app.run(debug=True, host=os.getenv('HOST'), port=5001)