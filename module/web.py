"""web ui for media download"""

import logging
import os

from flask import Flask, jsonify, render_template, request

import utils
import threading
from flask_login import LoginManager, login_required, login_user, UserMixin
from module.app import Application
from module.download_stat import (
    DownloadState,
    get_download_result,
    get_download_state,
    get_total_download_speed,
    set_download_state,
)
from utils.format import format_byte
from utils.crypto import AesBase64

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

_flask_app = Flask(__name__)

_flask_app.secret_key = "tdl"

_login_manager = LoginManager()
_login_manager.login_view = "login"
_login_manager.init_app(_flask_app)

web_login_users: dict = {}
#deAesCrypt = DeAesCrypt("1234123412ABCDEF")
deAesCrypt = AesBase64('1234123412ABCDEF', 'ABCDEF1234123412')
class User(UserMixin):
    """Web Login User"""

    id = "root"


@_login_manager.user_loader
def load_user(id):
    """
    Load a user object from the user ID.

    Returns:
        User: The user object.
    """
    return User()

def get_flask_app() -> Flask:
    """get flask app instance"""
    return _flask_app

def run_web_server(app : Application):
    """
    Runs a web server using the Flask framework.
    """

    get_flask_app().run(app.web_host, app.web_port, debug=app.debug_web, use_reloader=False)

# pylint: disable = W0603
def init_web(app: Application):
    """
    Set the value of the users variable.

    Args:
        users: The list of users to set.

    Returns:
        None.
    """
    global web_login_users
    if app.web_login_secret:
        web_login_users = {"root": app.web_login_secret}
    else:
        _flask_app.config["LOGIN_DISABLED"] = True
    if  app.debug_web:
        threading.Thread(target=run_web_server, args=(app,)).start()
    else:
        threading.Thread(
            target=get_flask_app().run, daemon=True, args=(app.web_host, app.web_port)
        ).start()


@_flask_app.route("/login", methods=["GET", "POST"])
def login():
    """
    Function to handle the login route.

    Parameters:
    - No parameters

    Returns:
    - If the request method is "POST" and the username and
      password match the ones in the web_login_users dictionary,
      it returns a JSON response with a code of "1".
    - Otherwise, it returns a JSON response with a code of "0".
    - If the request method is not "POST", it returns the rendered "login.html" template.
    """
    if request.method == "POST":
        username = "root"  # request.form['username']
        web_login_form = {}
        for key, value in request.form.items():
            if value:
                #value = deAesCrypt.decrypt(value, 64)
                #value = aes_cbc_decrypt_js_text(value,'1234123412ABCDEF', 'ABCDEF1234123412')
                value = deAesCrypt.decrypt(value)
            web_login_form[key] = value
    
        if not web_login_form.get("password"):
            return jsonify({"code": "0"})

        password = web_login_form["password"]
        if username in web_login_users and web_login_users[username] == password:
            user = User()
            login_user(user)
            return jsonify({"code": "1"})

        return jsonify({"code": "0"})

    return render_template("login.html")



@_flask_app.route("/")
@login_required
def index():
    """Index html"""
    return render_template(
        "index.html",
        download_state=(
            "pause" if get_download_state() is DownloadState.Downloading else "pause"
        ),
    )


@_flask_app.route("/get_download_status")
@login_required
def get_download_speed():
    """Get download speed"""
    return (
        '{ "download_speed" : "'
        + format_byte(get_total_download_speed())
        + '/s" , "upload_speed" : "0.00 B/s" } '
    )


@_flask_app.route("/set_download_state", methods=["POST"])
@login_required
def web_set_download_state():
    """Set download state"""
    state = request.args.get("state")

    if state == "continue" and get_download_state() is DownloadState.StopDownload:
        set_download_state(DownloadState.Downloading)
        return "pause"

    if state == "pause" and get_download_state() is DownloadState.Downloading:
        set_download_state(DownloadState.StopDownload)
        return "continue"

    return state


@_flask_app.route("/get_app_version")
def get_app_version():
    """Get telegram_media_downloader version"""
    return utils.__version__


@_flask_app.route("/get_download_list")
@login_required
def get_download_list():
    """get download list"""
    if request.args.get("already_down") is None:
        return "[]"

    already_down = request.args.get("already_down") == "true"

    download_result = get_download_result()
    result = "["
    for chat_id, messages in download_result.items():
        for idx, value in messages.items():
            is_already_down = value["down_byte"] == value["total_size"]

            if already_down and not is_already_down:
                continue

            if result != "[":
                result += ","
            download_speed = format_byte(value["download_speed"]) + "/s"
            result += (
                '{ "chat":"'
                + f"{chat_id}"
                + '", "id":"'
                + f"{idx}"
                + '", "filename":"'
                + os.path.basename(value["file_name"])
                + '", "total_size":"'
                + f'{format_byte(value["total_size"])}'
                + '" ,"download_progress":"'
            )
            result += (
                f'{round(value["down_byte"] / value["total_size"] * 100, 1)}'
                + '" ,"download_speed":"'
                + download_speed
                + '" ,"save_path":"'
                + value["file_name"].replace("\\", "/")
                + '"}'
            )

    result += "]"
    return result
