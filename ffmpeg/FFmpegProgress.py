import psycopg2
import time
import re

# Database connection details
db_host = "185.49.231.174"
db_user = "postgres"
db_password = "Mr0hVaaBtz"
db_name = "VOD"

# Log file path in the current directory
log_file_name = "sample-30s"
log_file_path = f"./{log_file_name}"

def get_last_log_entry():
    try:
        with open(log_file_path, 'r') as file:
            lines = file.readlines()
            if len(lines) >= 6:
                print("Retrieved log entry.")
                return lines[-6]  # Return the fifth line from the end
    except FileNotFoundError:
        print(f"Log file not found: {log_file_path}")
    except Exception as e:
        print(f"Error reading log file: {e}")
    return None

def extract_out_time(log_entry):
    match = re.search(r'out_time_ms=([0-9]+)', log_entry)  # Search for out_time_us instead of out_time
    if match:
        out_time_microseconds = int(match.group(1))  # Convert to integer
        out_time_seconds = out_time_microseconds / 1000000  # Convert microseconds to seconds
        print("Extracted out_time in seconds:", out_time_seconds)
        return str(out_time_seconds)  # Convert back to string if necessary
    else:
        print("No out_time found in log entry.")
    return None

def update_database(out_time, video_name):
    conn = None
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host
        )
        cursor = conn.cursor()
        query = "UPDATE \"TblConversionFlow\" SET \"FldProgress\" = %s WHERE \"FldFkLocalStream\" = %s"
        cursor.execute(query, (out_time, video_name))
        conn.commit()
        print("Database updated successfully.")
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error updating database: {error}")
    finally:
        if conn is not None:
            conn.close()

def main():
    while True:
        last_log_entry = get_last_log_entry()
        if last_log_entry:
            out_time = extract_out_time(last_log_entry)
            if out_time:
                update_database(out_time, log_file_name)
        else:
            print("Waiting for new log entries...")
        time.sleep(3)  # Wait for 10 seconds before repeating

if __name__ == "__main__":
    main()
