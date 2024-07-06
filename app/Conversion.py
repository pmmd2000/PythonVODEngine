import os
from tasks import process_video_task

def ConvertVideo(VideoID, VideoName,OriginalVideos_path,ConvertedVideos_path,VideoData):
    
    # Create converted video directory
    ConvertedVideo_path=os.path.join(ConvertedVideos_path,VideoName)
    os.makedirs(ConvertedVideo_path)
    if not os.path.exists(ConvertedVideo_path):
        raise Exception("Dir creation failed")
    
    # enc.key and enc.keyinfo creation
    EncKeyBytes=bytes.fromhex(VideoData['FldEncKey'])
    with open(os.path.join(ConvertedVideo_path,'enc.key'), 'wb') as f:
        f.write(EncKeyBytes)
    keyinfo=f"enc.key\n{ConvertedVideo_path}/enc.key"
    with open(os.path.join(ConvertedVideo_path,'enc.keyinfo'), 'w') as f:
        f.write(keyinfo)
    

    # FFmpeg Conversion:
    for Quality in [480,1080,720,360]:
        process_video_task.delay(VideoID, VideoName,OriginalVideos_path,ConvertedVideos_path,Quality)