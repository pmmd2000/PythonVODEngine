import ffmpeg

input_file = '/home/parham/videos/input.mp4'
output_file = '/home/parham/videos/converted/output.m3u8'

#FFmpeg conversion
(
ffmpeg
.input(input_file) # type: ignore
.output
    (
    output_file, 
    s='854x480', 
    vcodec='libx264', 
    max_muxing_queue_size=9999, 
    preset='veryfast', 
    start_number=0, 
    hls_time=4, 
    hls_list_size=0
    )
.run_async(pipe_stdout=False)
)