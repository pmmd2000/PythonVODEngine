from hashlib import sha256
import pymssql
from dotenv import load_dotenv
import os
from datetime import datetime
import redis

load_dotenv()

mssql_connection = pymssql.connect(
    server=os.getenv("DB_HOST","None"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME","None")
)

r = redis.Redis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)

hash_salt=os.getenv('HASH_SALT')
mssql_query_select_video="SELECT * FROM dbo.TblVideo WHERE FldName=%s"
mssql_query_select_conversion="SELECT * FROM dbo.TblConversion WHERE FldFkVideo=%s"
mssql_query_select_all="SELECT * FROM dbo.TblVideo INNER JOIN dbo.TblConversion ON FldPkVideo=FldFkVideo WHERE FldPkConversion=%s"
mssql_query_insert_video="INSERT INTO dbo.TblVideo (FldName,FldNameHash,FldExtension) VALUES (%s,%s,%s)"
mssql_query_insert_conversion="INSERT INTO dbo.TblConversion (FldFkVideo,FldInsertDatetime,FldEncKey,FldEncKeyIV,FldDuration) VALUES (%s,%s,%s,%s,%s)"
mssql_query_update_video = "UPDATE dbo.TblConversion SET {}=%s WHERE FldPkConversion=%s"


def mssql_select_video(VideoName):
    cursor = mssql_connection.cursor(as_dict=True)
    cursor.execute(mssql_query_select_video,(VideoName,))
    record = cursor.fetchone()
    cursor.close()
    return record

def mssql_insert_video(VideoName,Extension,Duration):
    video_name_hash=sha256((VideoName+hash_salt).encode('utf-8')).hexdigest()
    current_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    EncKeyHex = os.urandom(16).hex()
    EncKeyIVHex = os.urandom(16).hex()
    cursor = mssql_connection.cursor(as_dict=True)
    
    cursor.execute(mssql_query_insert_video,(VideoName,video_name_hash,Extension))
    mssql_connection.commit()
    
    cursor.execute(mssql_query_select_video,(VideoName,))
    VideoRecord = cursor.fetchone()
    VideoID=VideoRecord['FldPkVideo']
    
    cursor.execute(mssql_query_insert_conversion,(VideoID,current_datetime,EncKeyHex,EncKeyIVHex,Duration))
    mssql_connection.commit()
    
    cursor.execute(mssql_query_select_conversion,(VideoID,))
    ConversionRecord = cursor.fetchone()
    ConversionID=ConversionRecord['FldPkConversion']
    
    cursor.execute(mssql_query_select_all,(ConversionID,))
    record = cursor.fetchone()
    
    cursor.close()
    return record

def mssql_update_video_conversion_finished(ConversionID, ConversionState: bool):
    cursor = mssql_connection.cursor(as_dict=True)
    query = mssql_query_update_video.format("FldConvertIsFinished")
    cursor.execute(query, (int(ConversionState), ConversionID))
    mssql_connection.commit()
    cursor.close()

    
def redis_check_keyvalue(key):
    return r.get(key)