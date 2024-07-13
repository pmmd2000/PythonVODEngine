import functions
from celery_config import celery
import ffmpeg
import os
import re
import subprocess
import logging
import pymssql
import redis
from datetime import datetime

@celery.task(bind=True)
def process_video_task(self, VideoName, OriginalVideo_path, ConvertedVideos_path, Quality: int, VideoData):
    try:
        ###
        mssql_connection = pymssql.connect(
        server=os.getenv("DB_HOST","None"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME","None")
        )
        ConversionID=VideoData['FldPkConversion']
        def CurrentDatetime():
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        r = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)
        mssql_query_update_video = "UPDATE dbo.TblConversion SET {}=%s WHERE FldPkConversion=%s"
        def redis_check_keyvalue(key):
            return r.get(key)
        def mssql_update_video_conversion_finished(ConversionID, ConversionState: bool,):
            cursor = mssql_connection.cursor(as_dict=True)
            query = mssql_query_update_video.format("FldConvertIsFinished")
            cursor.execute(query, (int(ConversionState), ConversionID))
            mssql_connection.commit()
            cursor.close()        
        def CheckConversionEndRedis(VideoID,ConversionID,VideoName):
            if all(redis_check_keyvalue(f"{VideoID}:{ConversionID}:{VideoName}-{res}") == '100' for res in [480, 720, 1080]):
                mssql_update_video_conversion_finished(ConversionID,True)
            else:
                pass
        def redis_update_video_quality(VideoID,ConversionID, video_name, Quality: int, QualityPercentile:float):
            if Quality in (480, 720, 1080):
                r.set(f"{VideoID}:{ConversionID}:{video_name}-{Quality}",str(QualityPercentile),ex=86400)
            else:
                raise TypeError("Quality not valid")
        def mssql_update_video_quality(ConversionID, Quality: int,StartorEnd):
            if Quality in (480, 720, 1080) and StartorEnd in ('Start','End'):
                cursor = mssql_connection.cursor(as_dict=True)
                query = mssql_query_update_video.format(f"FldConvert{Quality}{StartorEnd}")
                cursor.execute(query, (CurrentDatetime(), ConversionID))
                mssql_connection.commit()
                cursor.close()
            else:
                raise TypeError("Arguments not valid")
        
        ###
        Extension= VideoData['FldExtension']
        input_file = os.path.join(OriginalVideo_path, f'{VideoName}{Extension}')
        output_file = os.path.join(ConvertedVideos_path, VideoName, f'{Quality}_{VideoName}.m3u8')
        ffmpeg_segment_filename = os.path.join(ConvertedVideos_path, VideoName, f'{Quality}_{VideoName}_%04d.ts')
        keyinfo_file = os.path.join(ConvertedVideos_path, VideoName, 'enc.keyinfo')
        key_file = os.path.join(ConvertedVideos_path, VideoName, 'enc.key')
        VideoID = VideoData['FldPkVideo']
        
        if Quality == 480:
            ffmpeg_resolution = '854x480'
        elif Quality == 720:
            ffmpeg_resolution = '1280x720'
        elif Quality == 1080:
            ffmpeg_resolution = '1920x1080'
        else:
            raise Exception("Quality unacceptable")

        command = (
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
                hls_key_info_file=keyinfo_file,
                hls_allow_cache=1,
                hls_enc=1,
                hls_enc_key=key_file,
                hls_playlist_type='event',
            )
            .global_args('-progress', '-', '-loglevel', 'verbose')
            .compile()
        )
        mssql_update_video_quality(ConversionID,Quality,'Start')
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        total_duration = None
        percentage = 0
        
        duration_regex = re.compile(r"Duration: (\d+):(\d+):(\d+).(\d+)")
        time_regex = re.compile(r"time=(\d+):(\d+):(\d+).(\d+)")

        while True:
            line = process.stderr.readline()
            if line == '' and process.poll() is not None:
                break
            if line:
                if total_duration is None:
                    match = duration_regex.search(line)
                    if match:
                        hours = int(match.group(1))
                        minutes = int(match.group(2))
                        seconds = int(match.group(3))
                        milliseconds = int(match.group(4))
                        total_duration = hours * 3600 + minutes * 60 + seconds + milliseconds / 100.0
                        # print(f"Total duration: {total_duration} seconds")  # Debug output

                match = time_regex.search(line)
                if match and total_duration:
                    hours = int(match.group(1))
                    minutes = int(match.group(2))
                    seconds = int(match.group(3))
                    milliseconds = int(match.group(4))
                    elapsed_time = hours * 3600 + minutes * 60 + seconds + milliseconds / 100.0
                    percentage = (elapsed_time / total_duration) * 100
                    print(f"Elapsed time: {elapsed_time} seconds, Percentage: {percentage:.2f}%")  # Debug output
                    redis_update_video_quality(VideoID,ConversionID,VideoName,Quality,round(percentage,2))

        
        redis_update_video_quality(VideoID,ConversionID, VideoName, Quality, 100)
        CheckConversionEndRedis(VideoID,ConversionID, VideoName)
        mssql_update_video_quality(ConversionID,Quality,'End')
        MasterM3U8=functions.WriteMasterM3U8(VideoID,ConversionID,VideoName)
        with open(os.path.join(ConvertedVideos_path, VideoName, f'{VideoName}.m3u8'), 'w') as f:
            f.write(MasterM3U8)
        return output_file
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'exc_type': type(e).__name__, 'exc_message': str(e)}
        )
        raise

# Ensure Celery logging is set to INFO level
logging.basicConfig(level=logging.INFO)