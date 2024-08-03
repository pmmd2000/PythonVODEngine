import re
import os
import db_connections
import jwt
from functools import wraps
from flask import request
import redis
import functions
from hashlib import sha256

jwt_secret_key=os.getenv('JWT_SECRET_KEY')
hash_salt=os.getenv('HASH_SALT')
Symlink_path=os.getenv('CONVERTED_VIDEOS_SYMLINK_PATH')

r = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)

def RawVideoNameCheck(RawVideoName):
    RegExExtention= r'^[\w]+\.[\w]+$'
    RegExNameOnly= r'^[\w]+$'
    if re.match(RegExExtention, RawVideoName):
        VideoName,Extension=os.path.splitext(RawVideoName)
        return {'VideoName': VideoName, 'Extension': Extension}
    elif re.match(RegExNameOnly,RawVideoName):
        return {'VideoName': RawVideoName, 'Extension': '.mp4'}
    else:
        return "VideoName Invalid",400

def WriteMasterM3U8(ConversionID,VideoName,ConvertedVideos_path):
    MasterM3U8_1080=""
    MasterM3U8_720=""
    MasterM3U8_480=""
    if db_connections.redis_check_keyvalue(ConversionID,1080) == '100':
        MasterM3U8_1080=f'#EXT-X-STREAM-INF:BANDWIDTH=1900000,AVERAGE-BANDWIDTH=1400000,RESOLUTION=1920x1080,FRAME-RATE=25,CODECS="avc1.64001f,mp4a.40.2"\n1080_{VideoName}.m3u8\n'
    if db_connections.redis_check_keyvalue(ConversionID,720) == '100':
        MasterM3U8_720=f'#EXT-X-STREAM-INF:BANDWIDTH=700000,AVERAGE-BANDWIDTH=520000,RESOLUTION=1280x720,FRAME-RATE=25,CODECS="avc1.64001f,mp4a.40.2"\n720_{VideoName}.m3u8\n'
    if db_connections.redis_check_keyvalue(ConversionID,480) == '100':
        MasterM3U8_480=f'#EXT-X-STREAM-INF:BANDWIDTH=450000,AVERAGE-BANDWIDTH=400000,RESOLUTION=854x480,FRAME-RATE=25,CODECS="avc1.64001f,mp4a.40.2"\n480_{VideoName}.m3u8\n'
    MasterM3U8=f'#EXTM3U\n{MasterM3U8_1080}{MasterM3U8_720}{MasterM3U8_480}'
    output_file=os.path.join(ConvertedVideos_path, VideoName, f'{VideoName}.m3u8')
    with open(output_file, 'w') as f:
        f.write(MasterM3U8)
    SymlinkDir = os.path.join(Symlink_path,VideoName)
    file_absolute_path=os.path.join('/app',output_file)
    file_symlink_absolute_path=os.path.join('/app',SymlinkDir,f'{VideoName}.m3u8')
    functions.replace_m3u8_content(ConversionID,file_absolute_path,file_symlink_absolute_path)
    return MasterM3U8

# def scp(VideoID,ConversionID,VideoName,ConvertedVideos_path,destination):
    
def complete_url(base_url, *objects):
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    if base_url.startswith('/'):
        base_url = base_url[1:]
    path = ''
    for obj in objects:
        if not obj.startswith('/'):
            obj = '/' + obj
        if obj.endswith('/'):
            obj = obj[:-1]
        path += obj
    complete_url = base_url + path
    return complete_url

def jwt_required_admin(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_param = request.headers.get('Authorization')
        if not auth_param:
            return "Unauthorized", 401
        try:
            decoded = jwt.decode(auth_param, jwt_secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return "Unauthorized", 401
        except jwt.InvalidTokenError:
            return "Unauthorized", 401
        if decoded['role'] not in (1,2,3,8):
            return 'Forbidden!',403

        kwargs['jwt_payload'] = decoded
        return func(*args, **kwargs)
    return wrapper

# def create_symlinks(VideoName,ConvertedVideos_path):
def replace_m3u8_content(ConversionID,input_file,output_file):
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            if line.startswith('#'):
                if line.startswith('#EXT-X-KEY'):
                    key='enc.key'
                    value=r.hget(ConversionID,key)
                    if value:
                        outfile.write(line.replace(key,value))
                    else:
                        outfile.write(line)
                else:
                    outfile.write(line)
            else:
                key = line.strip()
                value = r.hget(ConversionID,key)
                if value:
                    outfile.write(value + '\n')
                else:
                    outfile.write(line)