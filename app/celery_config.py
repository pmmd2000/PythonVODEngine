from celery import Celery
import os

from dotenv import load_dotenv
load_dotenv()
def make_celery(app_name=__name__):
    redis_url = os.getenv('REDIS_CS')
    celery=Celery(app_name, backend=redis_url, broker=redis_url)
    celery.conf.update({
        'worker_concurrency': 4
    })
    return celery


celery = make_celery()