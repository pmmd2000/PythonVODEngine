from celery_config import celery
import ffmpeg
import os

@celery.task(bind=True)
def process_video_task(self, input_file, output_folder):
    try:
        # Ensure the output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Create the base name for the output files
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(output_folder, f'{base_name}.m3u8')
        
        # FFmpeg conversion
        (
            ffmpeg
            .input(input_file)
            .output(
                output_file, 
                s='854x480', 
                vcodec='libx264', 
                max_muxing_queue_size=9999, 
                preset='veryfast', 
                start_number=0, 
                hls_time=4, 
                hls_list_size=0,
                hls_segment_filename=os.path.join(output_folder, f'{base_name}_%03d.ts')
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
