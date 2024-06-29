from celery import Celery

def make_celery(app_name=__name__):
    redis_url = 'redis://185.49.231.174:6380/0'
    celery=Celery(app_name, backend=redis_url, broker=redis_url)
    celery.conf.update({
        'worker_concurrency': 1
    })
    return celery


celery = make_celery()