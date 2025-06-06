from celery import Celery
import os
from kombu import Exchange, Queue
from dotenv import load_dotenv
load_dotenv()

def make_celery(app_name=__name__):
    redis_url = os.getenv('REDIS_CS')
    broker_url = os.getenv('RABBITMQ_CS')
    celery = Celery(app_name, backend=redis_url, broker=broker_url)
    celery.conf.task_queues = [Queue('tasks', Exchange('tasks'), routing_key='tasks',queue_arguments={'x-max-priority': 10}),]
    celery.conf.task_acks_late= True
    celery.conf.worker_prefetch_multiplier=1
    celery.conf.worker_concurrency=os.getenv('CELERY_WORKER_CONCURRENCY', 3)
    celery.conf.task_queue_max_priority = 10
    celery.conf.task_default_priority = 5
    celery.conf.worker_max_tasks_per_child=1
    celery.conf.result_backend_thread_safe=True
    celery.conf.task_track_started=True
    celery.conf.broker_connection_timeout = 30
    celery.conf.broker_heartbeat = 30
    celery.conf.broker_connection_retry = True
    celery.conf.broker_connection_retry_on_startup = True
    celery.conf.broker_connection_max_retries = 10  # unlimited retries
    
    return celery

celery = make_celery()