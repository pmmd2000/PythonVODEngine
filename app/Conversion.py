import os
from app import db_connections
from tasks import process_video_task
import ffmpeg

def ConvertVideo(VideoName,OriginalVideos_path,ConvertedVideos_path,VideoData,Symlink_path):
    enc_key_filename=os.getenv('ENC_KEY_NAME')
    enc_keyinfo_filename=os.getenv('ENC_KEYINFO_NAME')
    # Create converted video directory
    ConvertedVideo_path=os.path.join(ConvertedVideos_path,VideoName)
    Symlink_Video_path=os.path.join(Symlink_path,VideoName)
    local_done_path=os.getenv('LOCAL_DONE_PATH')
    EncKey_File = os.path.join(local_done_path, VideoName, enc_key_filename)
    os.makedirs(ConvertedVideo_path)
    # os.makedirs(Symlink_Video_path)
    if not os.path.exists(ConvertedVideo_path):
        raise Exception("Dir creation failed")
    
    # enc.key and enc.keyinfo creation
    EncKeyBytes=bytes.fromhex(VideoData['FldEncKey'])
    EncKeyIVHex = VideoData['FldEncKeyIV']
    with open(os.path.join(ConvertedVideo_path,enc_key_filename), 'wb') as f:
        f.write(EncKeyBytes)
        ##enc.keyinfo PATH CHANGE
    keyinfo=f"{enc_key_filename}\n{EncKey_File}\n{EncKeyIVHex}"
    with open(os.path.join(ConvertedVideo_path,enc_keyinfo_filename), 'w') as f:
        f.write(keyinfo)
    ConversionID=VideoData['FldPkConversion']
    db_connections.mssql_insert_chunks(VideoName,ConversionID)
    # FFmpeg Conversion:
    for Quality in [480,1080,720]:
        if Quality==480:
            ffmpeg_resolution = '854x480'
            priority=5
        elif Quality==720:
            ffmpeg_resolution = '1280x720'
            priority=3
        elif Quality==1080:
            ffmpeg_resolution = '1920x1080'
            priority=1
            
        process_video_task.apply_async(args=(VideoName,OriginalVideos_path,ConvertedVideos_path,Quality,VideoData,ffmpeg_resolution),queue='tasks',priority=priority )
        
def get_video_duration(VideoName,Extension,OriginalVideos_path):
    video_path=os.path.join(OriginalVideos_path,f'{VideoName}{Extension}')
    probe = ffmpeg.probe(video_path)
    duration = float(probe['format']['duration'])
    return duration