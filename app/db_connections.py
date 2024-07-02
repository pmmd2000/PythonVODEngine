from hashlib import sha256
import pymssql
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

mssql_connection = pymssql.connect(
    server=os.getenv("DB_HOST","None"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME","None")
)

hash_salt=os.getenv('HASH_SALT')
mssql_query_select_video="SELECT * FROM dbo.TblVideo WHERE FldName=%s"
mssql_query_insert_video="INSERT INTO dbo.TblVideo (FldName,FldNameHash,FldInsertDatetime,FldEncKey) VALUES (%s,%s,%s,%s)"

def mssql_select_video(video_name):
    cursor = mssql_connection.cursor(as_dict=True)
    cursor.execute(mssql_query_select_video,(video_name,))
    record = cursor.fetchone()
    cursor.close()
    return record

def mssql_insert_video(video_name):
    video_name_hash=sha256((video_name+hash_salt).encode('utf-8')).hexdigest()
    current_datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    EncKeyHex = os.urandom(16).hex()
    cursor = mssql_connection.cursor(as_dict=True)
    cursor.execute(mssql_query_insert_video,(video_name,video_name_hash,current_datetime,EncKeyHex))
    mssql_connection.commit()
    cursor.execute(mssql_query_select_video,(video_name,))
    record = cursor.fetchone()
    cursor.close()
    return record
    