from celery import Celery
import os
from kombu import Exchange, Queue
from dotenv import load_dotenv
load_dotenv()

def make_celery(app_name=__name__):
    redis_url = os.getenv('REDIS_CS')
    celery = Celery(app_name, backend=redis_url, broker=redis_url)
    
    celery.conf.update({
        'worker_concurrency': 1,
        'task_queues': (
            Queue('video_480', Exchange('video'), routing_key='video.480', queue_arguments={'x-max-priority': 10}),
            Queue('video_720', Exchange('video'), routing_key='video.720', queue_arguments={'x-max-priority': 5}),
            Queue('video_1080', Exchange('video'), routing_key='video.1080', queue_arguments={'x-max-priority': 1}),
            ),
        'task_default_queue': 'default',
        'task_default_exchange': 'video',
        'task_default_routing_key': 'video.default',
        'task_default_priority': 5,
    })
    
    return celery

celery = make_celery()