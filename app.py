import logging
import os
import uuid
import yaml
from werkzeug.utils import secure_filename
import api
from celery import Celery
from celery.result import AsyncResult
from celery.utils.log import get_task_logger
from flask import Flask, redirect, render_template, request, send_from_directory, url_for
from flask_celery import make_celery
from rofl import ROFL
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
import redis
from OpenSSL import SSL, crypto
from self_sign_cert import gen_self_signed_cert


cert_dir = 'certificates'
CERT_FILE = 'certificate.crt'
KEY_FILE = 'app.key'

# context = SSL.Context(SSL.SSLv23_METHOD)
# cert, key = gen_self_signed_cert()
# open(os.path.join(cert_dir, CERT_FILE), "wt").write(cert)
# open(os.path.join(cert_dir, KEY_FILE), "wt").write(key)
# context.use_privatekey_file(os.path.join(cert_dir, KEY_FILE))
# context.use_certificate_file(os.path.join(cert_dir, CERT_FILE))


config_path = os.path.abspath(os.path.join(os.getcwd(), "config.yml"))
config = yaml.load(open(config_path), Loader=yaml.FullLoader)
rofl_folder = "14Xsw4xk6vUFINsyy1OH5937Rq98W4JHw"
GOOGLE_CLIENT_ID = api.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = api.GOOGLE_CLIENT_SECRET
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

app = Flask(__name__)
app.config.update(result_backend='redis://127.0.0.1:6379/0', broker_url='redis://127.0.0.1:6379/0')

rofl = ROFL("trained_knn_model.clf", retina=True, on_gpu=False, emotions=True)

celery = Celery(main=__name__, broker='redis://127.0.0.1:6379/0', backend='redis://127.0.0.1:6379/0')

# celery = make_celery(app)

logger = logging.getLogger(__name__)
celery_logger = get_task_logger(__name__)

formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
file_handler = logging.FileHandler(config['LOGFILE'])
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)

ioloop = asyncio.get_event_loop()

try:
    init_db_command()
except sqlite3.OperationalError:
    # Assume it's already been created
    pass

client = WebApplicationClient(GOOGLE_CLIENT_ID)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


def set_logger(logger):
    """Setup logger."""
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


logger = set_logger(logger)
celery_logger = set_logger(celery_logger)


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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config['ALLOWED_EXTENSIONS']


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
            os.getcwd(), config['UPLOAD_FOLDER'], secure_filename(file.filename)))
        filename, file_extension = os.path.splitext(path)

        # Set the uploaded file a uuid name
        filename_uuid = str(uuid.uuid4()) + file_extension
        path_uuid = os.path.abspath(os.path.join(os.getcwd(), config['UPLOAD_FOLDER'], filename_uuid))

        file.save(path_uuid)
        logger.info(f'the file {file.filename} has been successfully saved as {filename_uuid}')
        # processing.apply_async((filename_uuid, emotions, recognize, remember), link_error=error_handler.s())
        processing(filename_uuid, emotions, recognize, remember)
        return redirect('/')


@app.route('/thank')
def thank():
    """Process the image endpoint."""

    # async_result = AsyncResult(id=task.task_id, app=celery)
    # processing_result = async_result.get()

    return render_template('thank.html')


def send_file(filename):
    r = api.upload_video("video_output/" + filename, filename.split('/')[-1], folder_id=rofl_folder)
    _id = r['id']
    """Show result endpoint."""
    return "https://drive.google.com/file/d/" + _id + "/preview"


# async def run(filename, fps_factor, recog, remem, em):
#     await ioloop.run_in_executor(None, rofl.basic_run, "queue", filename, fps_factor, recog, remem, em)


@celery.task(name='celery.processing')
def processing(filename, em=True, recog=True, remem=True):
    """Celery function for the image processing."""

    # rofl = ROFL("trained_knn_model.clf", retina=True, on_gpu=False, emotions=True)

    celery_logger.info(f'{filename} is processing')

    # ioloop.run_until_complete(run(filename, 30, recog, remem, em))
    rofl.basic_run("queue", filename, fps_factor=30, recognize=recog, remember=remem, emotions=em)
    celery_logger.info(f'processing {filename} is finished')

    i = 30
    while not os.path.isfile("video_output/" + filename) and i != 0:
        import time
        time.sleep(1)
        i -= 1
    api.send_file_with_email(current_user.email, "Processed video",
                             "Thank you, that's your processed video",
                             "video_output/" + filename)
    os.remove("queue/" + filename)
    r = api.upload_video("video_output/" + filename, filename.split('/')[-1], folder_id=rofl_folder)
    _id = r['id']

    return filename


@celery.task
def error_handler(uuid):
    result = AsyncResult(uuid)
    exc = result.get(propagate=False)
    print('Task {0} raised exception: {1!r}\n{2!r}'.format(
          uuid, exc, result.traceback))


if __name__ == "__main__":
    # exec('celery -A app.celery worker --loglevel=info')
    # celery.worker_main()
    # task = processing.apply_async(('twice.mp4', True, False, False), ignore_result=True)
    # print(task)
    # print(celery.current_worker_task)
    # result = AsyncResult(id=task.task_id, app=celery).get()
    context = (os.path.join(cert_dir, CERT_FILE), os.path.join(cert_dir, KEY_FILE))
    app.run( ssl_context=context, debug=False, threaded=True, port='80')
