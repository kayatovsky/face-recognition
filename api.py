from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.discovery import build
import io
import pickle
import requests
import os
import os.path
import platform
import mimetypes
import base64
from apiclient import errors
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
import pprint as pp
import json
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


SCOPES = ['https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/gmail.send']
SERVICE_ACCOUNT_FILE = 'Emotions_Project-481579272f6a.json'
EMAIL_ACCOUNT_FILE = 'email_credentials.json'
NVR_ACCOUNT_FILE = 'nvr_cred.json'
nvr_server = 'https://nvr.miem.hse.ru/api/gdrive-upload'
nvr_key = 'https://nvr.miem.hse.ru/api/gdrive-upload/504'
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
GOOGLE_CLIENT_ID = '332884163839-cgsk3ta79lgoo2o2otcb2h8ck28cd1if.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'bIb1mKNZH18LC5lSeDj1QTMk'

EMAIL_FROM = "noreply@facerecognizer.com"

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
# email_cred = service_account.Credentials.from_service_account_file(EMAIL_ACCOUNT_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=credentials)
with open('Emotions_Project-481579272f6a.json', 'r') as j:
    data = json.load(j)
# delegated_credentials = credentials.with_subject(EMAIL_FROM)
# service = build('gmail', 'v1', credentials=delegated_credentials)

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
        return r
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

        return res.status_code


def edit_rooms(rooms, ids, tags):
    staff = zip(ids, tags)
    staff = dict(zip(rooms, staff))
    f = open("rooms.pickle", "wb")
    f.write(pickle.dumps(staff))


def create_message(sender, to, subject, message_text, file=None):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    msg = MIMEText(message_text)
    message.attach(msg)

    if file is not None:
        content_type, encoding = mimetypes.guess_type(file)

        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        main_type, sub_type = content_type.split('/', 1)
        if main_type == 'text':
            fp = open(file, 'rb')
            msg = MIMEText(fp.read(), _subtype=sub_type)
            fp.close()
        elif main_type == 'image':
            fp = open(file, 'rb')
            msg = MIMEImage(fp.read(), _subtype=sub_type)
            fp.close()
        elif main_type == 'audio':
            fp = open(file, 'rb')
            msg = MIMEAudio(fp.read(), _subtype=sub_type)
            fp.close()
        else:
            fp = open(file, 'rb')
            msg = MIMEBase(main_type, sub_type)
            msg.set_payload(fp.read())
            fp.close()
        filename = os.path.basename(file)
        msg.add_header('Content-Disposition', 'attachment', filename=filename)
        message.attach(msg)

    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}


def send_message(user_id, message):

  """Send an email message.
  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    message: Message to be sent.
  Returns:
    Sent Message.
  """
  try:
      service = get_service('token.pickle')
      message = (service.users().messages().send(userId=user_id, body=message).execute())
      print('Message Id: %s' % message['id'])
      return message

  except errors.HttpError as error:
      print('An error occurred: %s' % error)


def build_service():
    """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                f"{SERVICE_ACCOUNT_FILE}", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)
    return service


def get_service(path):
    with open(rf'{path}', 'rb') as token:
        creds = pickle.load(token)
    service = build('gmail', 'v1', credentials=creds)
    return service


def send_file_with_email(to:str, subject:str, message_text, file=None):
    # email_service = get_service('token.pickle')
    message = create_message(EMAIL_FROM, to, subject, message_text, file)
    send_message('me', message)


def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


# send_file_with_email('iasizykh@miem.hse.ru', 'Test', 'Test')
build_service()

# message = create_message(EMAIL_FROM, 'iasizykh@miem.hse.ru', 'Test', 'Testment')
# send_message('me', message)
# pp = pp.PrettyPrinter(indent=4)

# r = upload_video("video_output/twice.mp4", "twice.mp4", folder_id="14Xsw4xk6vUFINsyy1OH5937Rq98W4JHw")
# print(r)
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
