from types import NoneType
from flask import Flask, request
import os
from dotenv import load_dotenv
import db_connections
import Conversion
import functions
from werkzeug.utils import secure_filename
from pathlib import Path

app = Flask(__name__)
load_dotenv()

ConvertedVideos_path = str(os.getenv('CONVERTED_VIDEOS_PATH'))
Symlink_path=os.getenv('CONVERTED_VIDEOS_SYMLINK_PATH')
OriginalVideos_path= str(os.getenv('ORIGINAL_VIDEOS_PATH'))
VideoPkField = str(os.getenv("DB_VIDEOPK_FIELD"))
base_url = f"{os.getenv('PROTOCOL')}://{os.getenv('HOST')}"

@app.get('/api/getVideos')
@functions.jwt_required_admin
def video_list(jwt_payload):
    VideoData= db_connections.mssql_select_video_star()
    print(base_url)
    for video in VideoData:
        VideoName = video['VideoName']
        thumbnail = functions.complete_url(base_url,ConvertedVideos_path,VideoName,f'480_{VideoName}.png')
        video['thumbnail']=thumbnail
    return VideoData, 200

@app.post('/api/startVideoConversion') 
@functions.jwt_required_admin
def video_insert(jwt_payload):
    RawVideoName = request.json['VideoName']
    try:
        VideoFullName = functions.RawVideoNameCheck(RawVideoName)
        VideoName = VideoFullName['VideoName']
        Extension = VideoFullName['Extension']
        
        # Validate extension
        if not Extension.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            return "Invalid file extension", 400

        VideoData= db_connections.mssql_select_video(VideoName)
        ConvertedVideo_path=os.path.join(ConvertedVideos_path,VideoName)
        OriginalVideo_File=os.path.join(OriginalVideos_path,f'{VideoName}{Extension}')
        if type(VideoData)==NoneType and not os.path.exists(ConvertedVideo_path) and os.path.exists(OriginalVideo_File):
            Duration=Conversion.get_video_duration(VideoName,Extension,OriginalVideos_path)
            VideoData=db_connections.mssql_insert_video(VideoName,Extension,float(Duration))
            Conversion.ConvertVideo(VideoName,OriginalVideos_path,ConvertedVideos_path,VideoData,Symlink_path)
            return {'VideoID':VideoData['FldPkVideo'],'ConversionID':VideoData['FldPkConversion']},200
        elif os.path.exists(ConvertedVideo_path):
            return "Video already present", 406 
        elif not type(VideoData)==NoneType and not os.path.exists(ConvertedVideo_path):
            return 'Previously converted video missing', 406
        elif type(VideoData)==NoneType and not os.path.exists(OriginalVideo_File):
            return 'Video file missing', 404

    except Exception as e:
        return f"Error processing video name: {str(e)}", 400

@app.post('/api/uploadVideo')
@functions.jwt_required_admin
def video_upload(jwt_payload):
    if "file" not in request.files:
        return "No file part", 400
        
    file = request.files["file"]
    file_uuid = request.form.get("dzuuid")
    if not file_uuid:
        return "Missing upload ID", 400

    # Generate a unique filename to avoid overwriting
    filename = f"{file_uuid[:8]}_{secure_filename(file.filename)}"
    save_path = Path(OriginalVideos_path) / filename
    
    # Ensure upload directory exists
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    current_chunk = int(request.form["dzchunkindex"])
    
    try:
        with open(save_path, "ab") as f:
            f.seek(int(request.form["dzchunkbyteoffset"]))
            f.write(file.stream.read())
    except OSError as e:
        return f"Error saving file: {str(e)}", 500

    total_chunks = int(request.form["dztotalchunkcount"])

    if current_chunk + 1 == total_chunks:
        # Verify final file size
        if os.path.getsize(save_path) != int(request.form["dztotalfilesize"]):
            # Cleanup failed upload
            os.unlink(save_path)
            return "Size mismatch", 500
            
        # Optional: Verify file type
        if not filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            os.unlink(save_path)
            return "Invalid file type", 400

    return {"message": "Chunk upload successful", "filename": filename}, 200
    
@app.get('/api/getVideoProgress')
@functions.jwt_required_admin
def video_progress(jwt_payload):
    ConversionID=request.json['ConversionID']
    Quality=request.json['Quality']
    Progress=db_connections.redis_check_keyvalue(ConversionID,Quality)
    return Progress

@app.route("/done/<url_ConvertedVideo_path>/<url_filename>")
@functions.jwt_required
def serve_file(url_ConvertedVideo_path, url_filename, auth_param):
    ConvertedVideo_path=os.path.basename(url_ConvertedVideo_path)
    filename=os.path.basename(url_filename)
    filepath = os.path.join(ConvertedVideos_path, ConvertedVideo_path, filename)
    if os.path.islink(filepath):
        filepath = os.path.realpath(filepath)

    if not os.path.exists(filepath):
        return "404 Not Found", 404
    
    if filename.endswith(".m3u8"):
        with open(filepath, "r") as file:
            content = file.read()
            ip = functions.get_real_ip()
            octets = ip.split(".")  # type: ignore
            binary_octets = [f"{int(octet):08b}" for octet in octets]
            bin_ip = "".join(binary_octets)
            
            for counter, bit in enumerate(bin_ip, start=1):
                if bit == '1':
                    if len(str(counter)) == 1:
                        counter = f"0{counter}"
                    content = content.replace(f"_01{counter}.ts", f"_01{counter}_watermarked.ts")
