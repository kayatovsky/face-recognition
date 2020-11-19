from celery import Celery
from rofl import ROFL
import os
import api
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

api.credentials = service_account.Credentials.from_service_account_file(api.SERVICE_ACCOUNT_FILE, scopes=api.SCOPES)
api.service = build('drive', 'v3', credentials=api.credentials)
with open('Emotions_Project-481579272f6a.json', 'r') as j:
    api.data = json.load(j)

celery = Celery()
celery.config_from_object('celeryconfig')

rofl_folder = "14Xsw4xk6vUFINsyy1OH5937Rq98W4JHw"


def send_file(filename, link=''):
    r = api.upload_video("video_output/" + filename, filename.split('/')[-1], folder_id=rofl_folder)
    _id = r['id']
    """Show result endpoint."""
    return "https://drive.google.com/file/d/" + _id + "/" + link


@celery.task(name='celery.processing')  # name='celery.processing'
def processing(filename, em=False, recog=False, remember=False, email=None):
    """Celery function for the image processing."""
    rofl = ROFL("trained_knn_model.clf", retina=True, on_gpu=False, emotions=True)
    rofl.basic_run("queue", filename, emotions=em, recognize=recog, remember=remember, fps_factor=30)
    print(filename)
    i = 30
    while not os.path.isfile("video_output/" + filename) and i != 0:
        time.sleep(1)
        i -= 1
    vid_link = send_file(filename, link='view')
    if email is not None:
        api.send_file_with_email(email, "Processed video",
                                 "Thank you, that's your processed video\nHere is your video:\n" + vid_link)
    os.remove("queue/" + filename)


@celery.task(name='celery.processing_nvr')  # name='celery.processing_nvr'
def processing_nvr(data, email=None):
    """Celery function for the image processing."""
    room = data['room']
    date = data['date']
    time = data['time']
    filename = api.download_video_nvr(room, date, time)

    rofl = ROFL("trained_knn_model.clf", retina=True,
                on_gpu=False, emotions=True)
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
    os.remove("queue/" + filename)
    return filename
