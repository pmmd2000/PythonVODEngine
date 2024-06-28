from celery_config import celery
import ffmpeg
import os

@celery.task
def process_video_task(input_file, output_folder):
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    output_file = os.path.join(output_folder, os.path.basename(input_file))
    
    # FFmpeg conversion
    (
        ffmpeg
        .input(input_file) # type: ignore
        .output(
            output_file, 
            s='854x480', 
            vcodec='libx264', 
            max_muxing_queue_size=9999, 
            preset='veryfast', 
            start_number=0, 
            hls_time=4, 
            hls_list_size=0
        )
        .run()
    )
    
    return output_file

