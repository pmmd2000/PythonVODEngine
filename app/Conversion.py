import os
from tasks import process_video_task
import ffmpeg

def ConvertVideo(VideoName,OriginalVideos_path,ConvertedVideos_path,VideoData):
    
    # Create converted video directory
    ConvertedVideo_path=os.path.join(ConvertedVideos_path,VideoName)
    os.makedirs(ConvertedVideo_path)
    if not os.path.exists(ConvertedVideo_path):
        raise Exception("Dir creation failed")
    
    # enc.key and enc.keyinfo creation
    EncKeyBytes=bytes.fromhex(VideoData['FldEncKey'])
    EncKeyIVHex = VideoData['FldEncKeyIV']
    with open(os.path.join(ConvertedVideo_path,'enc.key'), 'wb') as f:
        f.write(EncKeyBytes)
    keyinfo=f"enc.key\n{ConvertedVideo_path}/enc.key\n{EncKeyIVHex}"
    with open(os.path.join(ConvertedVideo_path,'enc.keyinfo'), 'w') as f:
        f.write(keyinfo)
    

    # FFmpeg Conversion:
    for Quality in [480,1080,720]:
        if Quality==480:
            priority=5
        elif Quality==720:
            priority=3
        elif Quality==1080:
            priority=1
            
        process_video_task.apply_async(args=(VideoName,OriginalVideos_path,ConvertedVideos_path,Quality,VideoData),queue='tasks',priority=priority )
        
def get_video_duration(VideoName,Extension,OriginalVideos_path):
    video_path=os.path.join(OriginalVideos_path,f'{VideoName}{Extension}')
    probe = ffmpeg.probe(video_path)
    duration = float(probe['format']['duration'])
    return duration

def generate_thumbnail(VideoName,Extension,OriginalVideos_path,ConvertedVideos_path):
    video_path=os.path.join(OriginalVideos_path,f'{VideoName}{Extension}')
    thumbnail_path=os.path.join(ConvertedVideos_path,VideoName,f'thumbnail_{VideoName}.png')
    (
        ffmpeg
        .input(video_path, ss=0)
        .filter('scale', 1280, -1)
        .output(thumbnail_path, vframes=1)
        .run()
    )