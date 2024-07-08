from celery_config import celery
import ffmpeg
import os
import db_connections
import functions


@celery.task(bind=True)
def process_video_task(self, VideoName, OriginalVideo_path, ConvertedVideos_path,Quality:int, VideoData):
    try:
        input_file = os.path.join(OriginalVideo_path,f'{VideoName}.mp4')
        output_file = os.path.join(ConvertedVideos_path,VideoName, f'{Quality}_{VideoName}.m3u8')
        ffmpeg_segment_filename=os.path.join(ConvertedVideos_path,VideoName,f'{Quality}_{VideoName}_%04d.ts')
        keyinfo_file = os.path.join(ConvertedVideos_path,VideoName, 'enc.keyinfo')
        VideoID=VideoData['FldPkVideo']
        
        if Quality==480:
            ffmpeg_resolution = '854x480'
        elif Quality==720:
            ffmpeg_resolution = '1280x720'
        elif Quality==1080:
            ffmpeg_resolution = '1920x1080'
        elif Quality==360:
            ffmpeg_resolution = '640x360'
        else:
            raise Exception("Quality unacceptable")
        (
            ffmpeg
            .input(input_file)
            .output(
                output_file, 
                s=ffmpeg_resolution, 
                vcodec='libx264', 
                max_muxing_queue_size=9999, 
                preset='veryfast', 
                start_number=0, 
                hls_time=4, 
                hls_list_size=0,
                hls_segment_filename=ffmpeg_segment_filename,
                hls_key_info_file = keyinfo_file
            )
            .run()
        )
        db_connections.redis_update_video_quality(VideoID,VideoName,Quality,True)
        functions.CheckConversionEndRedis(VideoID,VideoName)
        
        
        return output_file
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'exc_type': type(e).__name__, 'exc_message': str(e)}
        )
        raise
