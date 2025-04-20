import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_postgres_connection():
    try:
        return psycopg2.connect(os.getenv('POSTGRES_CS'))
    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise

def insert_new_conversion(video_name: str):
    """
    Insert a new conversion record into PostgreSQL with minimal information
    """
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        insert_query = '''
        INSERT INTO public."TblConversionFlow" 
        ("FldFkLocalStream", "FldIsVOD") 
        VALUES (%s, %s)
        RETURNING "FldPkConversionFlow"
        '''
        
        cursor.execute(insert_query, (video_name, True))
        result = cursor.fetchone()
        conn.commit()
        
        return result["FldPkConversionFlow"]
        
    except psycopg2.Error as e:
        print(f"Error inserting into PostgreSQL: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
