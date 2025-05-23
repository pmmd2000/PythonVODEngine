import os

workers = int(os.environ.get('GUNICORN_PROCESSES', '12'))
threads = int(os.environ.get('GUNICORN_THREADS', '24'))
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:5000')
forwarded_allow_ips = '*'
secure_scheme_headers = { 'X-Forwarded-Proto': 'http' }