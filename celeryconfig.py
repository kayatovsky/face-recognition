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
    Queue('0', Exchange('0'), routing_key='0'),
    Queue('1', Exchange('1'), routing_key='1'),
    Queue('2', Exchange('2'), routing_key='2'),
    Queue('3', Exchange('3'), routing_key='3'),
    Queue('4', Exchange('4'), routing_key='4'),
    Queue('5', Exchange('5'), routing_key='5'),
    Queue('6', Exchange('6'), routing_key='6'),
    Queue('7', Exchange('7'), routing_key='7'),
)

CELERY_DEFAULT_QUEUE = 'normal'
CELERY_DEFAULT_EXCHANGE = 'normal'
CELERY_DEFAULT_ROUTING_KEY = 'normal'

CELERY_ROUTES = {
    # -- HIGH PRIORITY QUEUE -- #
    'app.celery.processing': {'queue': 'high'},
    # -- LOW PRIORITY QUEUE -- #
    'app.celery.processing_nvr': {'queue': 'low'},
}