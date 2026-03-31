"""web ui for media download"""

import json
import logging
import os
import threading

from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager, UserMixin, login_required, login_user

import utils
from module.app import Application, ChatDownloadConfig
from module.download_stat import (
    DownloadState,
    get_download_result,
    get_download_state,
    get_total_download_speed,
    set_download_state,
)
from utils.crypto import AesBase64
from utils.format import format_byte

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

_flask_app = Flask(__name__)

_flask_app.secret_key = "tdl"
_login_manager = LoginManager()
_login_manager.login_view = "login"
_login_manager.init_app(_flask_app)
web_login_users: dict = {}
deAesCrypt = AesBase64("1234123412ABCDEF", "ABCDEF1234123412")

# Global Application instance (set by init_web)
_app_instance: Application = None


class User(UserMixin):
    """Web Login User"""

    def __init__(self):
        self.sid = "root"

    @property
    def id(self):
        """ID"""
        return self.sid


@_login_manager.user_loader
def load_user(_):
    """
    Load a user object from the user ID.

    Returns:
        User: The user object.
    """
    return User()


def get_flask_app() -> Flask:
    """get flask app instance"""
    return _flask_app


def run_web_server(app: Application):
    """
    Runs a web server using the Flask framework.
    """

    get_flask_app().run(
        app.web_host, app.web_port, debug=app.debug_web, use_reloader=False
    )


# pylint: disable = W0603
def init_web(app: Application):
    """
    Set the value of the users variable.

    Args:
        users: The list of users to set.

    Returns:
        None.
    """
    global _app_instance
    global web_login_users
    _app_instance = app
    if app.web_login_secret:
        web_login_users = {"root": app.web_login_secret}
    else:
        _flask_app.config["LOGIN_DISABLED"] = True
    if app.debug_web:
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
        username = "root"
        web_login_form = {}
        for key, value in request.form.items():
            if value:
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
            "pause" if get_download_state() is DownloadState.Downloading else "continue"
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


@_flask_app.route("/get_config")
@login_required
def get_config():
    """Return current config (sanitized) for the web UI."""
    if _app_instance is None:
        return jsonify({"code": 0, "msg": "App not initialized"})
    return jsonify({"code": 1, "data": _app_instance.get_config_for_web()})


@_flask_app.route("/set_config", methods=["POST"])
@login_required
def set_config():
    """Update config from web UI form data."""
    if _app_instance is None:
        return jsonify({"code": 0, "msg": "App not initialized"})

    # Support both JSON and form-encoded data
    if request.is_json:
        cfg = request.get_json()
    else:
        cfg = {}
        for key, value in request.form.items():
            try:
                cfg[key] = json.loads(value)
            except (ValueError, TypeError):
                cfg[key] = value

    result = _app_instance.set_config_from_web(cfg)
    return jsonify(result)


@_flask_app.route("/get_chat_list")
@login_required
def get_chat_list():
    """Return chat list for chat management table."""
    if _app_instance is None:
        return jsonify({"code": 0, "msg": "App not initialized"})
    config = _app_instance.get_config_for_web()
    return jsonify({"code": 1, "data": config.get("chat", [])})


@_flask_app.route("/add_chat", methods=["POST"])
@login_required
def add_chat():
    """Add a new chat_id to config."""
    if _app_instance is None:
        return jsonify({"code": 0, "msg": "App not initialized"})

    chat_id = None
    if request.is_json:
        data = request.get_json()
        chat_id = data.get("chat_id")
    else:
        chat_id = request.form.get("chat_id")

    if not chat_id:
        return jsonify({"code": 0, "msg": "chat_id is required"})

    # Ensure chat_download_config entry exists
    if chat_id not in _app_instance.chat_download_config:
        _app_instance.chat_download_config[chat_id] = ChatDownloadConfig()

    # Add to config['chat'] list if not present
    chat_list = _app_instance.config.get("chat", [])
    existing_ids = {c.get("chat_id") for c in chat_list}
    if str(chat_id) not in existing_ids and chat_id not in existing_ids:
        chat_list.append({"chat_id": str(chat_id), "last_read_message_id": 0})
        _app_instance.config["chat"] = chat_list
        _app_instance.update_config(immediate=True)

    return jsonify({"code": 1, "msg": f"Chat {chat_id} added"})


@_flask_app.route("/remove_chat", methods=["POST"])
@login_required
def remove_chat():
    """Remove a chat_id from config."""
    if _app_instance is None:
        return jsonify({"code": 0, "msg": "App not initialized"})

    chat_id = None
    if request.is_json:
        data = request.get_json()
        chat_id = data.get("chat_id")
    else:
        chat_id = request.form.get("chat_id")

    if not chat_id:
        return jsonify({"code": 0, "msg": "chat_id is required"})

    # Remove from chat_download_config
    if chat_id in _app_instance.chat_download_config:
        del _app_instance.chat_download_config[chat_id]

    # Remove from config['chat'] list
    chat_list = _app_instance.config.get("chat", [])
    _app_instance.config["chat"] = [
        c for c in chat_list if str(c.get("chat_id")) != str(chat_id)
    ]
    _app_instance.update_config(immediate=True)

    return jsonify({"code": 1, "msg": f"Chat {chat_id} removed"})


@_flask_app.route("/test_save_path", methods=["POST"])
@login_required
def test_save_path():
    """Test if a save path is valid/writable."""
    path = None
    if request.is_json:
        data = request.get_json()
        path = data.get("save_path")
    else:
        path = request.form.get("save_path")

    if not path:
        return jsonify({"code": 0, "msg": "save_path is required"})

    try:
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".write_test")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test")
        os.remove(test_file)
        return jsonify({"code": 1, "msg": "Path is valid and writable"})
    except Exception as e:
        return jsonify({"code": 0, "msg": f"Path error: {str(e)}"})


@_flask_app.route("/select_folder", methods=["GET"])
@login_required
def select_folder():
    """Return subfolders of a given path for the folder browser."""
    path = request.args.get("path", "")

    # Default to root/driver list on Windows, home on Unix
    if not path:
        if os.name == "nt":
            # Windows: list drives
            drives = []
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if os.path.isdir(drive):
                    drives.append({"name": drive, "path": drive})
            return jsonify({"code": 1, "data": drives})
        path = os.path.expanduser("~")

    if not os.path.isdir(path):
        return jsonify({"code": 0, "msg": "Not a valid directory"})

    try:
        items = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isdir(full) and not name.startswith("."):
                items.append({"name": name, "path": full})
        return jsonify({"code": 1, "data": items})
    except PermissionError:
        return jsonify({"code": 0, "msg": "Permission denied"})
    except Exception as e:
        return jsonify({"code": 0, "msg": str(e)})
