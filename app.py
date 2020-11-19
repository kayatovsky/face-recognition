import logging
import os
import uuid
from werkzeug.utils import secure_filename
from celery.utils.log import get_task_logger
from flask import Flask, redirect, render_template, request, send_from_directory, url_for
from celery import Celery
from rofl import ROFL
import api
from datetime import datetime, date, timedelta
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
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user
)
from oauthlib.oauth2 import WebApplicationClient
import requests
import json
import sqlite3
from db import init_db_command
from user import User
import asyncio
import uuid
import yaml
import api
import time

app = Flask(__name__)
app.config.update(BEDUG=True, TESTING=True,
                  ALLOWED_EXTENSIONS=['mp4'], LOGFILE='app.log',
                  UPLOAD_FOLDER='queue', RESULT_FOLDER='video_output',
                  CELERY_BROKER_URL='redis://localhost:6379',
                  CELERY_RESULT_BACKEND='redis://localhost:6379')

celery = Celery(app.name)
celery.config_from_object('celeryconfig')

logger = logging.getLogger(__name__)
celery_logger = get_task_logger(__name__)

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler = logging.FileHandler(app.config['LOGFILE'])
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

cert_dir = 'certificates'
CERT_FILE = 'certificate.crt'
KEY_FILE = 'app.key'

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


def set_logger(logger):
    """Setup logger."""
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


logger = set_logger(logger)
celery_logger = set_logger(celery_logger)

app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# try:
#     init_db_command()
#     pass
# except sqlite3.OperationalError:
#     # Assume it's already been created
#     pass

client = WebApplicationClient(GOOGLE_CLIENT_ID)


@app.route('/')
def index():
    """Start page."""
    print(request.remote_addr)

    displayment = 'none'

    if current_user.is_authenticated:
        displayment = 'inline'
        user = current_user.name
        return render_template('upload.html', displayment=displayment, username=user)

    return render_template('index.html', displayment=displayment)


@app.route("/login")
def login():
    google_provider_cfg = api.get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")
    google_provider_cfg = api.get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
    else:
        return "User email not available or not verified by Google.", 400
    user = User(
        id_=unique_id, name=users_name, email=users_email, profile_pic=picture
    )

    # Doesn't exist? Add it to the database.
    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email, picture)

    # Begin user session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


def allowed_file(filename):
    """Check format of the file."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route("/nvr", methods=['POST'])
def nvr():
    if request.method == 'POST':
        hour = request.form['hour']
        minute = request.form['min']
        data = {'em': "emotions" in request.form,
                'recog': "recognize" in request.form,
                'remember': "remember" in request.form,
                'room': request.form['room'],
                'date': request.form['date'],
                'time': hour + ":" + minute}
        email = current_user.email
        processing_nvr.apply_async(args=[data, email], queue='low', priority=1)

        # processing(filename, emotions, recognize, remember)
        return redirect('/')


@app.route('/upload', methods=['POST'])
def upload():
    """Upload file endpoint."""
    if request.method == 'POST':
        if not request.files.get('file', None):
            msg = 'the request contains no file'
            logger.error(msg)
            return render_template('exception.html', text=msg)
        emotions = "emotions" in request.form
        recognize = "recognize" in request.form
        remember = "remember" in request.form

        file = request.files['file']
        if file and not allowed_file(file.filename):
            msg = f'the file {file.filename} has wrong extention'
            logger.error(msg)
            return render_template('exception.html', text=msg)

        path = os.path.abspath(os.path.join(
            os.getcwd(), app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
        filename, file_extension = os.path.splitext(path)

        # Set the uploaded file a uuid name
        filename_uuid = str(uuid.uuid4()) + file_extension
        path_uuid = os.path.abspath(os.path.join(os.getcwd(), app.config['UPLOAD_FOLDER'], filename_uuid))

        file.save(path_uuid)
        logger.info(f'the file {file.filename} has been successfully saved as {filename_uuid}')
        processing.apply_async((filename_uuid, emotions, recognize, remember, current_user.email,), queue='high', priority=4)
        return redirect('/')


# @app.route('/result/<filename>')
# def send_file(filename):
#     """Show result endpoint."""
#     return send_from_directory(os.path.abspath(os.path.join(os.getcwd(), app.config['RESULT_FOLDER'])),
#                                filename)

def send_file(filename, link=''):
    r = api.upload_video("video_output/" + filename, filename.split('/')[-1], folder_id=rofl_folder)
    _id = r['id']
    """Show result endpoint."""
    return "https://drive.google.com/file/d/" + _id + "/" + link


@celery.task()  # name='celery.processing'
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


@celery.task()  # name='celery.processing_nvr'
def processing_nvr(data, email=None):
    """Celery function for the image processing."""
    room = data['room']
    date = data['date']
    time = data['time']
    try:
        filename = api.download_video_nvr(room, date, time)
    except:
        msg = f'Searching file in NVR archive something went wrong'
        logger.error(msg)
        return render_template('exception.html', text=msg)

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


if __name__ == "__main__":
    # pip install eventlet (устанвливаем eventlet в терминале, один раз)

    # запускаем редис (или перезапускаем)
    # flower celery (пишем в терминале1)
    # celery -A app.celery worker --loglevel=info -n high -Q high -P eventlet
    # celery -A app.celery worker --loglevel=info -n lo1 -Q low -P eventlet
    # celery -A app.celery worker --loglevel=info -n lo2 -Q low -P eventlet
    # celery -A app.celery worker --loglevel=info -n lo3 -Q low -P eventlet
    # celery -A app.celery worker --loglevel=info -n lo3 -P eventlet
    # попробовать откатить селери до 3.1.24 примерно
    # попробовать другие версии eventlet
    if not os.path.isdir('video_output'):
        os.mkdir('video_output')
    if not os.path.isdir('queue'):
        os.mkdir('queue')

    try:
        init_db_command()
        pass
    except sqlite3.OperationalError:
        # Assume it's already been created
        pass
    context = (os.path.join(cert_dir, CERT_FILE), os.path.join(cert_dir, KEY_FILE))
    app.run(ssl_context=context, debug=True, threaded=True, port='80', host='127.0.0.1')
