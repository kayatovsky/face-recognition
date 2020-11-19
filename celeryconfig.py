import os
from kombu import Queue, Exchange
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
BROKER_URL = os.environ.get(
    'REDIS_URL', "redis://{host}:{port}/2".format(
        host=REDIS_HOST, port=str(REDIS_PORT)))
CELERY_RESULT_BACKEND = BROKER_URL
CELERYD_MAX_TASKS_PER_CHILD = 1
CELERYD_PREFETCH_MULTIPLIER = 1
CELERY_ACKS_LATE = True
CELERY_QUEUES = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('normal', Exchange('normal'), routing_key='normal'),
    Queue('low', Exchange('low'), routing_key='low'),
)

CELERY_DEFAULT_QUEUE = 'normal'
CELERY_DEFAULT_EXCHANGE = 'normal'
CELERY_DEFAULT_ROUTING_KEY = 'normal'

CELERY_ROUTES = {
    # -- HIGH PRIORITY QUEUE -- #
    'celery.processing': {'queue': 'high'},
    # -- LOW PRIORITY QUEUE -- #
    'celery.processing_nvr_': {'queue': 'low'},
}