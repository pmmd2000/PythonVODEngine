from celery_config import celery
import ffmpeg
import os

@celery.task(bind=True)
def process_video_task(self, VideoName, OriginalVideo_path, ConvertedVideos_path,Quality):
    try:
        input_file = os.path.join(OriginalVideo_path,f'{VideoName}.mp4')
        output_file = os.path.join(ConvertedVideos_path,VideoName, f'{Quality}_{VideoName}.m3u8')
        
        if Quality==480:
            resolution = '854x480'
        elif Quality==720:
            resolution = '1280x720'
        elif Quality==1080:
            resolution = '1920x1080'
        elif Quality==360:
            resolution = '640x360'
        else:
            raise Exception("Quality unaccepted")
        (
            ffmpeg
            .input(input_file)
            .output(
                output_file, 
                s=resolution, 
                vcodec='libx264', 
                max_muxing_queue_size=9999, 
                preset='veryfast', 
                start_number=0, 
                hls_time=4, 
                hls_list_size=0,
                hls_segment_filename=os.path.join(ConvertedVideos_path,VideoName,f'{Quality}_{VideoName}_%03d.ts')
            )
            .run()
        )
        
        return output_file
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'exc_type': type(e).__name__, 'exc_message': str(e)}
        )
        raise
