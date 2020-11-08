import os

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
BROKER_URL = os.environ.get(
    'REDIS_URL', "redis://{host}:{port}/2".format(
        host=REDIS_HOST, port=str(REDIS_PORT)))
CELERY_RESULT_BACKEND = BROKER_URL
