import os
from kombu import Queue, Exchange
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
broker_url = os.environ.get(
    'REDIS_URL', "redis://{host}:{port}/2".format(
        host=REDIS_HOST, port=str(REDIS_PORT)))
result_backend = broker_url

worker_max_tasks_per_child = 4
task_queues = (
    Queue('high', Exchange('high'), routing_key='high'),
    Queue('normal', Exchange('normal'), routing_key='normal'),
    Queue('low', Exchange('low'), routing_key='low'),
)

task_default_queue = 'normal'
task_default_exchange = 'normal'
task_default_routing_key = 'normal'

task_routes = {
    # -- HIGH PRIORITY QUEUE -- #
    'app.celery.processing': {'queue': 'high'},
    # -- LOW PRIORITY QUEUE -- #
    'app.celery.processing_nvr': {'queue': 'low'},
}