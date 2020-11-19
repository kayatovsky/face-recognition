import time
from datetime import datetime, date, timedelta
import api
import os
from rofl import ROFL
from app import send_file, processing_nvr
from multiprocessing import Process

#
# def processing_nvr_mutliporcessing(data, email=None):
#     """Celery function for the image processing."""
#     room = data['room']
#     date = data['date']
#     time = data['time']
#     filename = api.download_video_nvr(room, date, time, data['process'])
#
#     rofl = ROFL("trained_knn_model.clf", retina=True,
#                 on_gpu=False, emotions=True)
#     rofl.basic_run("queue", filename.split('/')[1], emotions=data['em'],
#                    recognize=data['recog'], remember=data['remember'],
#                    fps_factor=30)
#     print(filename)
#     i = 30
#     while not os.path.isfile("video_output/" + filename) and i != 0:
#         time.sleep(1)
#         i -= 1
#     vid_link = send_file(filename, link='view')
#     if email is not None:
#         api.send_file_with_email(email, "Processed video",
#                                  "Thank you, that's your processed video\nHere is your video:\n" + vid_link)
#     os.remove("queue/" + filename)
#

if __name__ == "__main__":
    date_begin = date(2020, 2, 6)
    time_begin = datetime(1, 1, 1, 9, 30)
    time_end = datetime(1, 1, 1, 16, 00)
    data = {}
    data['room'] = '504'
    data['em'] = False
    data['recog'] = False
    data['remember'] = False
    date_end = datetime.now().date()
    while date_begin <= date_end:
        while time_begin <= time_end:
            data['date'] = date_begin.strftime('%Y-%m-%d')
            data['time'] = time_begin.strftime('%H:%M')
            print(data)
            processing_nvr.apply_async(args=[data], queue='low', priority=1)
            time.sleep(40)
            time_begin += timedelta(minutes=30)
        date_begin += timedelta(days=1)

    #  celery worker -A tasks.celery --loglevel=info -n low1 -Q low -P eventlet

    # p1 = Process(target=processing_nvr_mutliporcessing, args=[data])
    # time_begin += timedelta(minutes=30)
    # data['process'] = '2'
    # data['time'] = time_begin.strftime('%H:%M')
    # print(data)
    # p2 = Process(target=processing_nvr_mutliporcessing, args=[data])
    # time_begin += timedelta(minutes=30)
    # data['process'] = '3'
    # data['time'] = time_begin.strftime('%H:%M')
    # print(data)
    # p3 = Process(target=processing_nvr_mutliporcessing, args=[data])
    # time_begin += timedelta(minutes=30)
    # data['process'] = '4'
    # data['time'] = time_begin.strftime('%H:%M')
    # print(data)
    # p4 = Process(target=processing_nvr_mutliporcessing, args=[data])
    #
    # p1.start()
    # p2.start()
    # p3.start()
    # p4.start()
    #
    # p1.join()
    # time.sleep(40)
    # p2.join()
    # time.sleep(40)
    # p3.join()
    # time.sleep(40)
    # p4.join()
    # time.sleep(40)
