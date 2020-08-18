from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io
import pickle
import requests
import os
import platform
import pprint as pp
import datetime

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'Emotions Project-481579272f6a.json'
NVR_ACCOUNT_FILE = 'nvr_cred.json'
nvr_server = 'https://nvr.miem.hse.ru/api/gdrive-upload'
nvr_key = 'https://nvr.miem.hse.ru/api/gdrive-upload/504'

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)

# credentials = service_account.Credentials.from_service_account_file(NVR_ACCOUNT_FILE, scopes=SCOPES)
# service = build('drive', 'v3', credentials=credentials)

def look_into_drive(dict_id, name_contains=None):
    if name_contains is None:
        return service.files().list(pageSize=100,
                                    fields="nextPageToken, files(id, name, mimeType, parents, createdTime, permissions, quotaBytesUsed)",
                                    q="'" + dict_id + "' in parents").execute()
    return service.files().list(pageSize=100,
                                fields="nextPageToken, files(id, name, mimeType, parents, createdTime, permissions, quotaBytesUsed)",
                                q="'" + dict_id + "' in parents and name contains '" + name_contains + "'").execute()


def download_video_nvr(room, date, time, filename=None, need_folder=False):
    try:
        rooms = pickle.loads(open("rooms.pickle", "rb").read())
    except:
        raise Exception("No file containing rooms' ids")
    room_id = rooms[room][0]
    tag = rooms[room][1]
    results = look_into_drive(room_id, date)
    if len(results['files']) > 1:
        raise Exception("More then one directory on Google drive")
    elif len(results['files']) == 0:
        raise Exception("No files found on drive")
    time_id = results['files'][0]['id']
    results = look_into_drive(time_id, time)
    if len(results['files']) > 1:
        raise Exception("More then one directory on Google drive")
    elif len(results['files']) == 0:
        raise Exception("No files found on drive")
    if tag is not None:
        results = look_into_drive(results['files'][0]['id'], date + "_" + time + "_" + room + "_" + tag)
        if filename is None:
            [hour, minute] = time.split(":")
            filename = "queue/" + date + "_" + hour + "-" + minute + "_" + room + "_" + tag + ".mp4"
    if len(results['files']) > 1:
        raise Exception("More then one file on Google drive")
    elif len(results['files']) == 0:
        raise Exception("No files found on drive")
    request = service.files().get_media(fileId=results['files'][0]['id'])
    fh = io.FileIO(filename, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print("Download process is %d%%. " % int(status.progress() * 100))

    if need_folder:
        return results['files'][0]['parents']
    else:
        return filename


def upload_video(filename, upload_name, folder_id=None, room_num=None):
    if folder_id is not None:
        file_metadata = {'name': upload_name, 'parents': [folder_id]}
        media = MediaFileUpload(filename, resumable=True)
        r = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(r)
        os.remove(filename)
        return 0
    elif room_num is not None:
        if platform.system() != "Windows":
            old_string = filename
            _dir, old_string = old_string.split("/")
            old_string = old_string.split(".")[0]
            d = datetime.datetime.strptime(old_string, "%Y-%m-%d_%H-%M")
            new_string = _dir + "/" + d.strftime("%Y-%m-%d_%H:%M") + ".mp4"
            os.rename(filename, new_string)
            filename = new_string
        file = open(filename, 'rb')
        files = {'file': file}
        res = requests.post(nvr_server + "/" + room_num, files=files, headers=nvr_key)
        os.remove(filename)

        return res.status_code


def edit_rooms(rooms, ids, tags):
    staff = zip(ids, tags)
    staff = dict(zip(rooms, staff))
    f = open("rooms.pickle", "wb")
    f.write(pickle.dumps(staff))


# pp = pprint.PrettyPrinter(indent=4)


# now = datetime.datetime.now()
# today = now.strftime('%Y-%m-%d')
#
# filename, results = download_video_nvr('504', '2020-07-12', '12:00')
# results = upload_video('1zAPs-2GP_SQj6tHLWwgohjuwCS_7o3yu', 'Webcam.mp4')
# pp.pprint(results)


# rooms = ['504', '520', '305', '505a', '307', '306']
# ids = ['1zAPs-2GP_SQj6tHLWwgohjuwCS_7o3yu', '1hjRds9U673yqZq6sjPuoLT3R0-zzr-B3', '1i3j8a60gk-RtX6vS3md8q98xtbc5VSk-',
#        '14JWOQs_dW8aIHpQZfO-KQ9HKQVqrwLN9', '1qZNnDJpIBZI52CcEcwAJP69QR9LyIPi2', '1INi7xUvLhPJW0as3HO8ugdCgsO-HwfxB']
# tags = ['26', None, '54', None, None, None]
# edit_rooms(rooms, ids, tags)
