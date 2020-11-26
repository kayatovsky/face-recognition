import time
from datetime import datetime, date, timedelta
import api
import os
from rofl import ROFL
from celery import Celery
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json


celery = Celery(__name__)
celery.config_from_object('celeryconfig')

rofl_folder = "14Xsw4xk6vUFINsyy1OH5937Rq98W4JHw"

api.credentials = service_account.Credentials.from_service_account_file(api.SERVICE_ACCOUNT_FILE, scopes=api.SCOPES)
api.service = build('drive', 'v3', credentials=api.credentials)
with open('Emotions_Project-481579272f6a.json', 'r') as j:
    api.data = json.load(j)
# api.build_service()
GOOGLE_CLIENT_ID = api.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = api.GOOGLE_CLIENT_SECRET
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)


def send_file(filename, link=''):
    r = api.upload_video("video_output/" + filename, filename.split('/')[-1], folder_id=rofl_folder)
    _id = r['id']
    """Show result endpoint."""
    return "https://drive.google.com/file/d/" + _id + "/" + link


@celery.task(name='stream.processing_nvr_', time_limit=14000)  # name='stream.processing_nvr_'
def processing_nvr_(data, filename=None, email=None):
    """Celery function for the image processing."""
    room = data['room']
    date = data['date']
    time = data['time']
    try:
        filename = api.download_video_nvr(room, date, time)
    except:
        msg = f'Searching file in NVR archive something went wrong'
    rofl = ROFL("trained_knn_model.clf", retina=True,
                on_gpu=False, emotions=True)
    print(filename)
    rofl.basic_run("queue", filename.split('/')[1], emotions=data['em'],
                   recognize=data['recog'], remember=data['remember'],
                   fps_factor=30)
    print(filename)
    i = 30
    while not os.path.isfile("video_output/" + filename) and i != 0:
        time.sleep(1)
        i -= 1
    vid_link = send_file(filename, link='view')
    if email is not None:
        api.send_file_with_email(email, "Processed video",
                                 "Thank you, that's your processed video\nHere is your video:\n" + vid_link)
    # api.upload_video()  # сюда правильно написать функцию отправки видео
    os.remove("queue/" + filename)


def stream(date_begin, time_begin, time_end, n=4):
    data = {}
    data['room'] = '504'
    data['em'] = False
    data['recog'] = False
    data['remember'] = False
    date_end = datetime.now().date()
    p = {}
    m = 60
    h = 3600
    while date_begin <= date_end:
        data['date'] = date_begin.strftime('%Y-%m-%d')
        time_begin = datetime(1, 1, 1, 9, 30)
        while time_begin <= time_end:
            for i in range(n):
                data['time'] = time_begin.strftime('%H:%M')
                print(data)
                p[str(i)] = processing_nvr_.apply_async(args=[data], queue=str(i), priority=i)
                time.sleep(5)
                time_begin += timedelta(minutes=30)
            flag = False
            while not flag:
                flag = True
                for i in range(n):
                    if not p[str(i)].ready():
                        flag = False
                        break
                time.sleep(5 * m)
        while date_begin == date_end:
            time.sleep(18 * h)
            date_end = datetime.now().date()
        date_begin += timedelta(days=1)


if __name__ == "__main__":
    date_begin = date(2020, 2, 6)
    time_begin = datetime(1, 1, 1, 9, 30)  # время 9:30
    time_end = datetime(1, 1, 1, 16, 00)  # время 16:00
    workers = 4  # сюда писать количество воркеров
    stream(date_begin, time_begin, time_end, workers)


    #  celery purge
    #  celery worker -A stream.celery --loglevel=info -n 0 -Q 0 -P eventlet
    #  celery worker -A stream.celery --loglevel=info -n 1 -Q 1 -P eventlet
    #  celery worker -A stream.celery --loglevel=info -n 2 -Q 2 -P eventlet
    #  celery worker -A stream.celery --loglevel=info -n 3 -Q 3 -P eventlet
    #  celery worker -A stream.celery --loglevel=info -n 4 -Q 4 -P eventlet
    #  celery worker -A stream.celery --loglevel=info -n 5 -Q 5 -P eventlet
    #  celery worker -A stream.celery --loglevel=info -n 6 -Q 6 -P eventlet
    #  celery worker -A stream.celery --loglevel=info -n 7 -Q 7 -P eventlet
