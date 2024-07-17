from celery_config import celery
import ffmpeg
import os
import re
import subprocess
import logging
import pymssql
import redis
from datetime import datetime
from hashlib import sha256
import functions

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
        watermark_path=os.getenv('WATERMARK_PATH')
        hash_salt=os.getenv('HASH_SALT')
        ConversionID=VideoData['FldPkConversion']
        def CurrentDatetime():
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        r = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)
        mssql_query_update_video = "UPDATE dbo.TblConversion SET {}=%s WHERE FldPkConversion=%s"
        mssql_query_insert_chunk= "INSERT INTO dbo.TblChunk (FldFkConversion,FldChunkName,FldChunkHash,FldChunkExtension) VALUES (%s,%s,%s,%s)"
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
        def mssql_insert_chunks(VideoID,ConversionID,Quality,VideoName):
            OutputDir = os.path.join(ConvertedVideos_path, VideoName)
            cursor = mssql_connection.cursor(as_dict=True)
            for file in os.listdir(OutputDir):
                if file.startswith(str(Quality)):
                    ChunkName,ChunkExtension=os.path.splitext(file)
                    ChunkHash=sha256((ChunkName+hash_salt).encode('utf-8')).hexdigest()
                    r.hset(f'{VideoID}:{ConversionID}:{VideoName}',file,ChunkHash)
                    cursor.execute(mssql_query_insert_chunk,(ConversionID,ChunkName,ChunkHash,ChunkExtension))
            mssql_connection.commit()
            cursor.close()
        def watermark_video(ConvertedVideos_path,VideoName,Quality,VideoData,watermark_path):
            EncKey=VideoData['FldEncKey']
            EncKeyIV=VideoData['FldEncKeyIV']
            print('entered the function')
            for index in range(101,133):
                encrypted_input_file=os.path.join(ConvertedVideos_path,VideoName,f'{Quality}_{VideoName}_0{index}.ts')
                if os.path.exists(encrypted_input_file):
                    decrypted_input_file=os.path.join(ConvertedVideos_path,VideoName,f'{Quality}_{VideoName}_0{index}_b.ts')
                    decrypted_watermarked_file=os.path.join(ConvertedVideos_path,VideoName,f'{Quality}_{VideoName}_0{index}_e.ts')
                    encrypted_watermarked_file=os.path.join(ConvertedVideos_path,VideoName,f'{Quality}_{VideoName}_0{index}_watermarked.ts')
                    watermark_file=os.path.join(watermark_path,f'watermark_{Quality}.png')
                    openssl_decrypt_command = [
                    "openssl",
                    "aes-128-cbc",
                    "-d",
                    "-in", encrypted_input_file,
                    "-out", decrypted_input_file,
                    "-iv", EncKeyIV,
                    "-K", EncKey
                    ]
                    subprocess.run(openssl_decrypt_command, check=True)
                    ffmpeg_inwatermark=ffmpeg.input(watermark_file)
                    (
                        ffmpeg
                        .input(decrypted_input_file)
                        .overlay(ffmpeg_inwatermark)
                        .output(decrypted_watermarked_file, vcodec='libx264', acodec='copy', copyts=None, vsync=0, muxdelay=0)
                        .run()
                    )
                    openssl_encrypt_command = [
                    "openssl",
                    "aes-128-cbc",
                    "-e",
                    "-in", decrypted_watermarked_file,
                    "-out", encrypted_watermarked_file,
                    "-iv", EncKeyIV,
                    "-K", EncKey
                    ]
                    subprocess.run(openssl_encrypt_command, check=True)
                    os.remove(decrypted_input_file)
                    os.remove(decrypted_watermarked_file)
                    
                else:
                    pass
        ###
        Extension= VideoData['FldExtension']
        input_file = os.path.join(OriginalVideo_path, f'{VideoName}{Extension}')
        output_file = os.path.join(ConvertedVideos_path, VideoName, f'{Quality}_{VideoName}.m3u8')
        ffmpeg_segment_filename = os.path.join(ConvertedVideos_path, VideoName, f'{Quality}_{VideoName}_%04d.ts')
        keyinfo_file = os.path.join(ConvertedVideos_path, VideoName, 'enc.keyinfo')
        key_file = os.path.join(ConvertedVideos_path, VideoName, 'enc.key')
        VideoID = VideoData['FldPkVideo']
        thumbnail_path=os.path.join(ConvertedVideos_path,VideoName,f'{Quality}_{VideoName}.png')
        
        if Quality == 480:
            ffmpeg_resolution = '854x480'
        elif Quality == 720:
            ffmpeg_resolution = '1280x720'
        elif Quality == 1080:
            ffmpeg_resolution = '1920x1080'
        else:
            raise Exception("Quality unacceptable")
        (
            ffmpeg
            .input(input_file, ss=0)
            .filter('scale', -1,Quality)
            .output(thumbnail_path, vframes=1, update=1)
            .run()
        )
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
                hls_playlist_type='vod',
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
        watermark_video(ConvertedVideos_path,VideoName,Quality,VideoData,watermark_path)
        mssql_insert_chunks(VideoID,ConversionID,Quality,VideoName)
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