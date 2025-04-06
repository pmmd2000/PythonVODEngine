import re
import os
import db_connections
import jwt
from functools import wraps
from flask import request
import redis

auth_api_secret=os.getenv('AUTH_API_SECRET')
auth_api_host=os.getenv('AUTH_API_HOST')
jwt_secret_key=os.getenv('JWT_SECRET_KEY')
user_jwt_secret_key=os.getenv('USER_JWT_SECRET_KEY')
hash_salt=os.getenv('HASH_SALT')
Symlink_path=os.getenv('CONVERTED_VIDEOS_SYMLINK_PATH')

r = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)

def RawVideoNameCheck(RawVideoName):
    # Validate filename with regex
    pattern = r'^[a-zA-Z0-9_-]+\.[a-zA-Z0-9]+$'
    if not re.match(pattern, RawVideoName):
        return None
        
    # Extract name and extension
    VideoName, Extension = os.path.splitext(RawVideoName)
    # Return as dictionary instead of tuple
    return {
        'VideoName': VideoName,
        'Extension': Extension
    }

def WriteMasterM3U8(ConversionID,VideoName,ConvertedVideos_path):
    MasterM3U8_1080=""
    MasterM3U8_720=""
    MasterM3U8_480=""
    if db_connections.redis_check_keyvalue(ConversionID,1080) == '100':
        MasterM3U8_1080=f'#EXT-X-STREAM-INF:BANDWIDTH=1900000,AVERAGE-BANDWIDTH=1400000,RESOLUTION=1920x1080,FRAME-RATE=25,CODECS="avc1.64001f,mp4a.40.2"\n1080_{VideoName}_1.m3u8\n'
    if db_connections.redis_check_keyvalue(ConversionID,720) == '100':
        MasterM3U8_720=f'#EXT-X-STREAM-INF:BANDWIDTH=700000,AVERAGE-BANDWIDTH=520000,RESOLUTION=1280x720,FRAME-RATE=25,CODECS="avc1.64001f,mp4a.40.2"\n720_{VideoName}_1.m3u8\n'
    if db_connections.redis_check_keyvalue(ConversionID,480) == '100':
        MasterM3U8_480=f'#EXT-X-STREAM-INF:BANDWIDTH=450000,AVERAGE-BANDWIDTH=400000,RESOLUTION=854x480,FRAME-RATE=25,CODECS="avc1.64001f,mp4a.40.2"\n480_{VideoName}_1.m3u8\n'
    MasterM3U8=f'#EXTM3U\n{MasterM3U8_1080}{MasterM3U8_720}{MasterM3U8_480}'
    output_file=os.path.join(ConvertedVideos_path, VideoName, f'{VideoName}_1.m3u8')
    with open(output_file, 'w') as f:
        f.write(MasterM3U8)
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
        if decoded['role'] not in (1,3,8):
            return 'Forbidden!',403

        kwargs['jwt_payload'] = decoded
        return func(*args, **kwargs)
    return wrapper

def jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        video_dir = kwargs.get("url_ConvertedVideo_dir")

        # Bypass authentication for video_dir that starts with specific prefixes
        if video_dir and (video_dir.startswith("karabiz") or video_dir.startswith("Karabiz") or video_dir.startswith("Azmoon")):
            kwargs['auth_param'] = None
            return func(*args, **kwargs)

        auth_param = request.args.get("auth")
        if not auth_param:
            return "Unauthorized", 401

        try:
            decoded = jwt.decode(auth_param, user_jwt_secret_key, algorithms=["HS256"], options={"verify_exp": False, "verify_nbf": False})
        except jwt.exceptions.ImmatureSignatureError:
            pass
        except jwt.ExpiredSignatureError:
            return "Unauthorized", 401
        except jwt.InvalidSignatureError:
            return "Malformed", 420
        except jwt.DecodeError:
            return "Server Error", 500
        except jwt.InvalidTokenError:
            return "Unauthorized", 400

        
        local_stream = decoded.get("localStream")
        if local_stream != video_dir:
            return "Unauthorized", 401

        remote_ip = get_real_ip()
        jwt_ip = decoded.get("ip")
        if remote_ip != jwt_ip:
            return "Unauthorized", 403

        kwargs['auth_param'] = auth_param
        return func(*args, **kwargs)
    return wrapper


# def create_symlinks(VideoName,ConvertedVideos_path):
def replace_m3u8_content(ConversionID,input_file,token):
    enc_key_filename=os.getenv('ENC_KEY_NAME')
    enc_keyinfo_filename=os.getenv('ENC_KEYINFO_NAME')
    with open(input_file, 'r') as infile:
        response=''
        values=r.hgetall(ConversionID)
        for line in infile:
            if line.startswith('#'):
                if line.startswith('#EXT-X-KEY'):
                    key=enc_key_filename
                    value=values.get(key)
                    if value:
                        response += line.replace(key , value) + '?auth=' + token + '\n'
                    else:
                        response += line + '\n'
                else:
                    response += line + '\n'
            else:
                key = line.strip()
                file_number = int(key.split('_')[-1].split('.')[0])
                if 101 <= file_number <= 132:
                    tsname,extension = os.path.splitext(key)
                    key = tsname + '_watermarked' + extension
                value=values.get(key)
                if value:
                    response += value + '?auth=' + token + '\n'
                else:
                    response += line + '\n'
    return response
                    
def get_real_ip():
    if not request.headers.getlist("X-Forwarded-For"):
        ip = request.remote_addr
    else:
        ip = request.headers.getlist("X-Forwarded-For")[0]
    return ip

def replace_auth_params(content, auth_param):
    content = re.sub(r'(?<=enc_1)\.key\b', f'.key?auth={auth_param}', content)
    content = re.sub(r'\.ts\b', f'.ts?auth={auth_param}', content)
    content = re.sub(r'\.m3u8\b', f'.m3u8?auth={auth_param}', content)
    return content