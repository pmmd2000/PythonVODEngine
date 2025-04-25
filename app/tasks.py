import fnmatch
from genericpath import isfile
import shutil
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
import paramiko
import socket
import tempfile
import contextlib
import json
import requests

@celery.task(bind=True)
def process_video_task(self, VideoName, OriginalVideo_path, ConvertedVideos_path, Quality: int, VideoData,ffmpeg_resolution):

    remote_host=os.getenv('REMOTE_HOST')
    remote_username=os.getenv('REMOTE_USER')
    remote_pass=os.getenv('REMOTE_PASS')
    remote_original_path=os.getenv('REMOTE_ORIGINAL_PATH')
    remote_done_path=os.getenv('REMOTE_DONE_PATH')
    remote_storage2_host=os.getenv('REMOTE_STORAGE2_HOST')
    remote_storage2_username=os.getenv('REMOTE_STORAGE2_USER')
    remote_storage2_pass=os.getenv('REMOTE_STORAGE2_PASS')
    remote_storage2_done_path=os.getenv('REMOTE_STORAGE2_DONE_PATH')
    remote_storage1_host=os.getenv('REMOTE_STORAGE1_HOST')
    remote_storage1_username=os.getenv('REMOTE_STORAGE1_USER')
    remote_storage1_pass=os.getenv('REMOTE_STORAGE1_PASS')
    remote_storage1_done_path=os.getenv('REMOTE_STORAGE1_DONE_PATH')
    remote_storage1_original_path=os.getenv('REMOTE_STORAGE1_ORIGINAL_PATH')
    remote_storage1_done_ssd_path=os.getenv('REMOTE_STORAGE1_DONE_SSD_PATH')
    remote_storage1_done_ssdback_path=os.getenv('REMOTE_STORAGE1_DONE_SSDBACK_PATH')
    VideoID = VideoData['FldPkVideo']
    local_done_path=os.getenv('LOCAL_DONE_PATH')
    local_done_videopath=os.path.join(local_done_path,str(Quality)+"_"+VideoName)
    local_original_path=os.getenv('LOCAL_ORIGINAL_PATH')
    local_original_videopath=os.path.join(local_original_path,str(Quality)+"_"+VideoName)
    enc_key_filename=os.getenv('ENC_KEY_NAME')
    enc_keyinfo_filename=os.getenv('ENC_KEYINFO_NAME')
    
    # Create required directories if they don't exist
    os.makedirs(local_done_path, exist_ok=True)
    os.makedirs(local_original_path, exist_ok=True)
    os.makedirs(local_done_videopath, exist_ok=True)
    os.makedirs(local_original_videopath, exist_ok=True)
    
    try:
        
        mssql_connection = pymssql.connect(
        server=os.getenv("DB_HOST","None"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME","None")

        )
        r = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), password=os.getenv('REDIS_PASS'), decode_responses=True)
        mssql_query_update_video = "UPDATE dbo.TblConversion SET {}=%s WHERE FldPkConversion=%s"
        mssql_query_insert_chunk= "INSERT INTO dbo.TblChunk (FldFkConversion,FldChunkName,FldChunkHash,FldChunkExtension) VALUES (%s,%s,%s,%s)"
        watermark_path=os.getenv('WATERMARK_PATH')
        hash_salt=os.getenv('HASH_SALT')
        ConversionID=VideoData['FldPkConversion']
        Extension= VideoData['FldExtension']
        Symlink_path = os.getenv('CONVERTED_VIDEOS_SYMLINK_PATH')

        def MP4Transfer():
            try:
                remote_file=os.path.join(remote_original_path,f"{VideoName}{Extension}")
                local_file=os.path.join(local_original_videopath,f"{VideoName}{Extension}")
                if os.path.exists(local_file):
                    return logging.info(f"Skipping transfer, {VideoName}{Extension} already exists")
                ssh=paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(remote_host,username=remote_username,password=remote_pass)
                sftp=ssh.open_sftp()
                sftp.get(remote_file, local_file)
                logging.info(f"{VideoName}{Extension} transferred")
                sftp.close()
                ssh.close()
            except Exception as e:
                logging.basicConfig()
                raise
        
        def fileTransfer (direction: str, VideoName: str, Quality: int = None):
            try:

                if direction == 'send':
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(remote_host, username=remote_username, password=remote_pass)
                    sftp = ssh.open_sftp()
                    ssh1 = paramiko.SSHClient()
                    ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh1.connect(remote_storage1_host, username=remote_storage1_username, password=remote_storage1_pass)
                    sftp1 = ssh1.open_sftp()
                    ssh2 = paramiko.SSHClient()
                    ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh2.connect(remote_storage2_host, username=remote_storage2_username, password=remote_storage2_pass)
                    sftp2 = ssh2.open_sftp()
                    remote_dir_png = os.path.join(remote_done_path, VideoName,f"{Quality}_{VideoName}_1.png")
                    local_dir_png = os.path.join(local_done_videopath, VideoName,f"{Quality}_{VideoName}_1.png")
                    sftp.put(local_dir_png, remote_dir_png)
                    try:
                        sftp1.mkdir(os.path.join(remote_storage1_done_ssd_path, VideoName))
                        sftp1.mkdir(os.path.join(remote_storage1_done_ssdback_path, VideoName))
                        sftp2.mkdir(os.path.join(remote_storage2_done_path, VideoName))
                        sftp2.chown(os.path.join(remote_storage2_done_path, VideoName), 1000, 1000)
                    except IOError:
                        pass  # Directory might already exist

                    local_dir = os.path.join(local_done_videopath, VideoName)
                    remote_dir1 = os.path.join(remote_storage1_done_ssd_path, VideoName)
                    remote_dir2 = os.path.join(remote_storage2_done_path, VideoName)
                    
                    files_to_transfer = [
                        f"{Quality}_{VideoName}_1.m3u8",
                        f"{VideoName}_1.m3u8",
                        enc_key_filename,
                        f"{Quality}_{VideoName}_1.png"
                    ]
                    ts_pattern = f"{Quality}_{VideoName}*.ts"
                    for file in os.listdir(local_dir):
                        if fnmatch.fnmatch(file, ts_pattern):
                            files_to_transfer.append(file)
                    # Transfer each file
                    for filename in files_to_transfer:
                        local_file = os.path.join(local_dir, filename)
                        remote_file1 = os.path.join(remote_dir1, filename)
                        remote_file2 = os.path.join(remote_dir2, filename)
                        if os.path.exists(local_file):
                            sftp1.put(local_file, remote_file1)
                            sftp2.put(local_file, remote_file2)
                            sftp2.chown(remote_file2, 1000, 1000)

                    # --- UPDATED CODE: Copy files from storage2 SSD to SSD backup and symlink the folder ---
                    # Copy each file from SSD to SSD backup
                    for filename in files_to_transfer:
                        remote_file2_ssd = os.path.join(remote_dir1, filename)
                        remote_dir2_ssdback = os.path.join(remote_storage1_done_ssdback_path, VideoName)
                        remote_file2_ssdback = os.path.join(remote_dir2_ssdback, filename)
                        try:
                            sftp1.stat(remote_file2_ssd)  # Ensure file exists
                            copy_cmd = f'cp "{remote_file2_ssd}" "{remote_file2_ssdback}"'
                            ssh1.exec_command(copy_cmd)
                        except Exception as e:
                            logging.error(f"Failed to copy {filename} to SSD backup on storage2: {e}")

                    # Create symlink for the folder (not individual files)
                    try:
                        # # Remove the actual done path folder if it exists and is not a symlink
                        # ssh2.exec_command(f'if [ -d "{remote_dir2}" ] && [ ! -L "{remote_dir2}" ]; then rm -rf "{remote_dir2}"; fi')
                        # Create symlink from SSD folder to actual done path
                        symlink_cmd = f'ln -s {remote_dir1}/ {remote_storage1_done_path}'
                        logging.info(symlink_cmd)
                        ssh1.exec_command(symlink_cmd)
                    except Exception as e:
                        logging.error(f"Failed to symlink SSD folder to actual done path on storage2: {e}")
                    # --- END UPDATED CODE ---

                elif direction == 'receive':
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(remote_host, username=remote_username, password=remote_pass)
                    sftp = ssh.open_sftp()
                    # Create local directory if it doesn't exist
                    os.makedirs(os.path.join(local_done_videopath, VideoName), exist_ok=True)

                    files_to_receive = [enc_key_filename]
                    remote_dir = os.path.join(remote_done_path, VideoName)
                    local_dir = os.path.join(local_done_videopath, VideoName)

                    for filename in files_to_receive:
                        remote_file = os.path.join(remote_dir, filename)
                        local_file = os.path.join(local_dir, filename)
                        try:
                            sftp.get(remote_file, local_file)
                            logging.info(f"Received {filename} from remote server")
                        except FileNotFoundError:
                            logging.error(f"Remote file not found: {filename}")

                else:
                    raise ValueError("Direction must be either 'send' or 'receive'")


            except Exception as e:
                logging.error(f"File transfer failed: {e}")
                raise


        def CurrentDatetime():
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        def redis_check_keyvalue(key):
            return r.get(key)
        def mssql_update_video_conversion_finished(ConversionID, ConversionState: bool,):
            cursor = mssql_connection.cursor(as_dict=True)
            query = mssql_query_update_video.format("FldConvertIsFinished")
            cursor.execute(query, (int(ConversionState), ConversionID))
            mssql_connection.commit()
            cursor.close()    
        def CheckConversionEndRedis(ConversionID):
            if all(redis_check_keyvalue(f"{ConversionID}:{res}") == '100' for res in [480, 720, 1080]):
                mssql_update_video_conversion_finished(ConversionID,True)
            else:
                pass
        def redis_update_video_quality(ConversionID, Quality: int, QualityPercentile:float):
            if Quality in (480, 720, 1080):
                r.set(f"{ConversionID}:{Quality}", str(QualityPercentile), ex=86400)
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
        # duplicate function
        def cleanup():
            if os.path.isfile(os.path.join(local_original_videopath,f"{VideoName}{Extension}")):
                os.remove(os.path.join(local_original_videopath,f"{VideoName}{Extension}"))
                os.rmdir(os.path.join(local_original_videopath))
                logging.info(f"Original {VideoName}{Extension} file removed")
            if os.path.exists(os.path.join(local_done_videopath,VideoName)):
                for filename in os.listdir(os.path.join(local_done_videopath,VideoName)):
                    file_path=os.path.join(local_done_videopath,VideoName,filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print('Failed to delete %s. Reason: %s' % (file_path, e))
                os.rmdir(os.path.join(local_done_videopath,VideoName))
                os.rmdir(os.path.join(local_done_videopath))
                logging.info(f"Converted {VideoName} directory removed")
        def mssql_insert_chunks(ConversionID,Quality,VideoName):
            OutputDir = os.path.join(local_done_videopath, VideoName)
            SymlinkDir = os.path.join(Symlink_path,VideoName)
            cursor = mssql_connection.cursor(as_dict=True)
            for file in (file for file in os.listdir(OutputDir) if file.startswith(str(Quality))):
                ChunkName,ChunkExtension=os.path.splitext(file)
                ChunkHash=sha256((ChunkName+hash_salt).encode('utf-8')).hexdigest()[:16]
                r.hset(ConversionID,file,ChunkHash+ChunkExtension)
                file_absolute_path=os.path.join('/app',OutputDir,file)
                file_symlink_absolute_path=os.path.join('/app',SymlinkDir,f'{ChunkHash}{ChunkExtension}')
                cursor.execute(mssql_query_insert_chunk,(ConversionID,ChunkName,ChunkHash,ChunkExtension))
                # os.symlink(file_absolute_path,file_symlink_absolute_path)
            mssql_connection.commit()
            cursor.close()
        def watermark_video(local_done_videopath,VideoName,Quality,VideoData,watermark_path):
            EncKey=VideoData['FldEncKey']
            EncKeyIV=VideoData['FldEncKeyIV']
            print('entered the function')
            for index in range(101,133):
                encrypted_input_file=os.path.join(local_done_videopath,VideoName,f'{Quality}_{VideoName}_1{index}.ts')
                if os.path.exists(encrypted_input_file):
                    decrypted_input_file=os.path.join(local_done_videopath,VideoName,f'{Quality}_{VideoName}_1{index}_b.ts')
                    decrypted_watermarked_file=os.path.join(local_done_videopath,VideoName,f'{Quality}_{VideoName}_1{index}_e.ts')
                    encrypted_watermarked_file=os.path.join(local_done_videopath,VideoName,f'{Quality}_{VideoName}_l{index}.ts')
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
                        .output(decrypted_watermarked_file, vcodec='libx264', acodec='copy', copyts=None, fps_mode='passthrough' ,map="0:a", muxdelay=0)
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

        def _handle_progress_socket(sock, total_duration, ConversionID, Quality):
            """Helper function to handle FFmpeg progress updates via socket"""
            connection, _ = sock.accept()
            data = ""
            with connection:
                while True:
                    try:
                        chunk = connection.recv(1024).decode()
                        if not chunk:
                            break
                        data += chunk
                        lines = data.split('\n')
                        data = lines.pop()  # Keep incomplete line for next iteration
                        
                        logging.debug("Socket data received: %s", chunk)
                        
                        for line in lines:
                            if not line:
                                continue
                            key, _, value = line.partition('=')
                            key, value = key.strip(), value.strip()
                            
                            logging.debug("Progress key-value: %s = %s", key, value)
                            
                            if key == 'out_time_us':
                                try:
                                    elapsed_time = float(value) / 1000000  # Convert microseconds to seconds
                                    if elapsed_time > 0:  # Only update if we have valid time
                                        percentage = min((elapsed_time / total_duration) * 100, 100)
                                        logging.info("Conversion progress: %.2f%%", percentage)
                                        redis_update_video_quality(ConversionID, Quality, round(percentage, 2))
                                except ValueError:
                                    logging.warning("Invalid time value received: %s", value)
                                    continue
                            elif key == 'progress':
                                if value in ('end', 'error'):
                                    logging.info("FFmpeg progress status: %s", value)
                                    return value
                    except Exception as e:
                        logging.error("Error processing FFmpeg progress: %s", str(e))
                        continue  # Keep trying to process progress updates

        def ffmpeg_conversion(ConversionID, Quality, ffmpeg_resolution):
            OriginalVideo_Name = os.path.join(local_original_videopath, f'{VideoName}{Extension}')
            ConvertedVideo_m3u8 = os.path.join(local_done_videopath, VideoName, f'{Quality}_{VideoName}_1.m3u8')
            Thumbnail_Path = os.path.join(local_done_videopath, VideoName, f'{Quality}_{VideoName}_1.png')
            FFmpegSegment_Name = os.path.join(local_done_videopath, VideoName, f'{Quality}_{VideoName}_1%d.ts')
            EncKeyInfo_File = os.path.join(local_done_videopath, VideoName, enc_keyinfo_filename)
            EncKey_File = os.path.join(local_done_videopath, VideoName, enc_key_filename)
            EncKeyIVHex = VideoData['FldEncKeyIV']
            keyinfo=f"{enc_key_filename}\n{EncKey_File}\n{EncKeyIVHex}"

            with open(os.path.join(local_done_videopath,VideoName,enc_keyinfo_filename), 'w') as f:
                f.write(keyinfo)
            # Generate thumbnail first
            (
                ffmpeg
                .input(OriginalVideo_Name, ss=0)
                .filter('scale', -1, Quality)
                .output(Thumbnail_Path, vframes=1, update=1)
                .run()
            )

            # Get video duration
            probe = ffmpeg.probe(OriginalVideo_Name)
            total_duration = float(probe['format']['duration'])

            # Create temporary socket for progress monitoring
            socket_path = tempfile.mktemp()
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(socket_path)
            sock.listen(1)

            try:
                mssql_update_video_quality(ConversionID, Quality, 'Start')
                
                # Create log files
                log_dir = os.path.join(local_done_videopath, VideoName, 'logs')
                os.makedirs(log_dir, exist_ok=True)
                ffmpeg_log_file = os.path.join(log_dir, f'ffmpeg_{Quality}.log')
                
                command = (
                    ffmpeg
                    .input(OriginalVideo_Name)
                    .output(
                        ConvertedVideo_m3u8,
                        s=ffmpeg_resolution,
                        vcodec='libx264',
                        max_muxing_queue_size=9999,
                        preset='veryfast',
                        start_number=0,
                        hls_time=10,
                        hls_list_size=0,
                        hls_segment_filename=FFmpegSegment_Name,
                        hls_key_info_file=EncKeyInfo_File,
                        hls_allow_cache=1,
                        hls_playlist_type='vod'
                    )
                    .global_args('-progress', f'unix://{socket_path}')
                    .overwrite_output()
                    .compile()
                )

                # Start FFmpeg process with output redirection
                with open(ffmpeg_log_file, 'w') as log_file:
                    process = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=1  # Line buffered
                    )
                    
                    # Start separate threads to handle stdout and stderr
                    def log_output(pipe, prefix):
                        for line in pipe:
                            log_file.write(f"{prefix}: {line}")
                            log_file.flush()
                            logging.debug("%s: %s", prefix, line.strip())
                    
                    import threading
                    stdout_thread = threading.Thread(target=log_output, args=(process.stdout, "STDOUT"))
                    stderr_thread = threading.Thread(target=log_output, args=(process.stderr, "STDERR"))
                    stdout_thread.start()
                    stderr_thread.start()
                    
                    # Monitor progress through socket
                    result = _handle_progress_socket(sock, total_duration, ConversionID, Quality)
                    
                    # Wait for process and logging threads to complete
                    process.wait()
                    stdout_thread.join()
                    stderr_thread.join()
                    
                    if process.returncode != 0 or result == 'error':
                        logging.error("FFmpeg conversion failed with return code: %d", process.returncode)
                        raise Exception(f"FFmpeg conversion failed. Check logs at {ffmpeg_log_file}")

            finally:
                # Cleanup
                sock.close()
                if os.path.exists(socket_path):
                    os.unlink(socket_path)

        def notify_conversion_status(video_name: str, status_type: int):
            """
            Notify the conversion status API
            status_type: 1 = started, 2 = ended, 3 = both
            """
            try:
                api_host = os.getenv('CONVERSION_API_HOST')
                api_secret = os.getenv('CONVERSION_API_SECRET')
                
                name = os.path.splitext(video_name)[0]
                
                payload = {
                    "localStream": name,
                    "type": status_type,
                    "secret": api_secret
                }
                
                headers = {
                    'accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                url = f"{api_host}/video/logUploadConvert"
                
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                logging.info(f"Successfully notified conversion status API for {name} with type {status_type}")
                
            except Exception as e:
                logging.error(f"Failed to notify conversion status: {str(e)}")

        # Add status notification at start
        notify_conversion_status(VideoName, 1)
        notify_conversion_status(VideoName, 3)
        MP4Transfer()
        fileTransfer('receive', VideoName, Quality)
        ffmpeg_conversion(ConversionID,Quality,ffmpeg_resolution)
        redis_update_video_quality(ConversionID, Quality, 100)
        watermark_video(local_done_videopath,VideoName,Quality,VideoData,watermark_path)
        mssql_insert_chunks(ConversionID,Quality,VideoName)
        functions.WriteMasterM3U8(ConversionID,VideoName,local_done_videopath)
        fileTransfer('send',VideoName,Quality)
        CheckConversionEndRedis(ConversionID)
        mssql_update_video_quality(ConversionID,Quality,'End')
        cleanup()

        # Add status notification at end
        notify_conversion_status(VideoName, 2)
        notify_conversion_status(VideoName, 3)

        return f"{ConversionID}:{Quality}"
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'exc_type': type(e).__name__, 'exc_message': str(e)}
        )
        raise

# Ensure log directory exists
log_dir = os.path.dirname(os.path.join(os.getenv('LOCAL_DONE_PATH'), 'conversion.log'))
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output to console
        logging.FileHandler(os.path.join(os.getenv('LOCAL_DONE_PATH'), 'conversion.log'))  # Output to file
    ]
)