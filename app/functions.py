import re
import os
import db_connections

def RawVideoNameCheck(RawVideoName):
    RegExExtention= r'^[\w]+\.[\w]+$'
    RegExNameOnly= r'^[\w]+$'
    if re.match(RegExExtention, RawVideoName):
        VideoName,Extension=os.path.splitext(RawVideoName)
        return VideoName
    elif re.match(RegExNameOnly,RawVideoName):
        return RawVideoName
    else:
        return "VideoName Invalid",400

def CheckConversionEnd(VideoName):
    VideoDetails= db_connections.mssql_select_video(VideoName)
    if all(VideoDetails[f'FldConvertState{res}'] == 1 for res in [480, 720, 1080, 360]):
        db_connections.mssql_update_video_conversion_finished(VideoName,True)
    else:
        pass
    
def CheckConversionEndRedis(VideoID,VideoName):
    if all(db_connections.redis_check_keyvalue(f"{VideoID}-{VideoName}-{res}") == '100' for res in [480, 720, 1080]):
        db_connections.mssql_update_video_conversion_finished(VideoName,True)
    else:
        pass