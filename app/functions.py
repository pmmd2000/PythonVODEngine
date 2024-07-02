import re
import os

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