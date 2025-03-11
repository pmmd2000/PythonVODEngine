import os
from app import db_connections
from tasks import process_video_task
import ffmpeg

def ConvertVideo(VideoName,OriginalVideos_path,ConvertedVideos_path,VideoData,Symlink_path):
    
    # Create converted video directory
    ConvertedVideo_path=os.path.join(ConvertedVideos_path,VideoName)
    Symlink_Video_path=os.path.join(Symlink_path,VideoName)
    os.makedirs(ConvertedVideo_path)
    # os.makedirs(Symlink_Video_path)
    if not os.path.exists(ConvertedVideo_path):
        raise Exception("Dir creation failed")
    
    # enc.key and enc.keyinfo creation
    EncKeyBytes=bytes.fromhex(VideoData['FldEncKey'])
    EncKeyIVHex = VideoData['FldEncKeyIV']
    with open(os.path.join(ConvertedVideo_path,'enc.key'), 'wb') as f:
        f.write(EncKeyBytes)
        ##enc.keyinfo PATH CHANGE
    keyinfo=f"enc.key\n/celery/done/{VideoName}/enc.key\n{EncKeyIVHex}"
    with open(os.path.join(ConvertedVideo_path,'enc.keyinfo'), 'w') as f:
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