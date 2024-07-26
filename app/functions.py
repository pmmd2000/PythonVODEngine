import re
import os
import db_connections

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

def WriteMasterM3U8(VideoID,ConversionID,VideoName,ConvertedVideos_path):
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
    with open(os.path.join(ConvertedVideos_path, VideoName, f'{VideoName}.m3u8'), 'w') as f:
        f.write(MasterM3U8)
    return MasterM3U8

# def scp(VideoID,ConversionID,VideoName,ConvertedVideos_path,destination):
    