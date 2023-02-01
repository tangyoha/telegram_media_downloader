"""web ui for media download"""

import logging
import os
import time

from flask import Flask, render_template, request

from utils.format import format_byte

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

_flask_app = Flask(__name__)

_download_result: dict = {}
_total_download_speed: int = 0
_total_download_size: int = 0
_last_download_time: float = time.time()


def get_flask_app() -> Flask:
    """get flask app instance"""
    return _flask_app


def get_download_result() -> dict:
    """get global download result"""
    return _download_result


def get_total_download_speed() -> int:
    """get total download speed"""
    return _total_download_speed


def update_download_status(
    message_id: int, down_byte: int, total_size: int, file_name: str, start_time: float
):
    """update_download_status"""
    cur_time = time.time()
    # pylint: disable = W0603
    global _total_download_speed
    global _total_download_size
    global _last_download_time

    if _download_result.get(message_id):
        last_download_byte = _download_result[message_id]["down_byte"]
        last_time = _download_result[message_id]["end_time"]
        download_speed = _download_result[message_id]["download_speed"]
        each_second_total_download = _download_result[message_id][
            "each_second_total_download"
        ]
        end_time = _download_result[message_id]["end_time"]

        _total_download_size += down_byte - last_download_byte
        each_second_total_download += down_byte - last_download_byte

        if cur_time - last_time >= 1.0:
            download_speed = int(each_second_total_download / (cur_time - last_time))
            end_time = cur_time
            each_second_total_download = 0

        download_speed = max(download_speed, 0)

        _download_result[message_id]["down_byte"] = down_byte
        _download_result[message_id]["end_time"] = end_time
        _download_result[message_id]["download_speed"] = download_speed
        _download_result[message_id][
            "each_second_total_download"
        ] = each_second_total_download
    else:
        each_second_total_download = down_byte
        _download_result[message_id] = {
            "down_byte": down_byte,
            "total_size": total_size,
            "file_name": file_name,
            "start_time": start_time,
            "end_time": cur_time,
            "download_speed": down_byte / (cur_time - start_time),
            "each_second_total_download": each_second_total_download,
        }
        _total_download_size += down_byte

    if cur_time - _last_download_time >= 1.0:
        # update speed
        _total_download_speed = int(
            _total_download_size / (cur_time - _last_download_time)
        )
        _total_download_speed = max(_total_download_speed, 0)
        _total_download_size = 0
        _last_download_time = cur_time


@_flask_app.route("/")
def index():
    """index html"""
    return render_template("index.html")


@_flask_app.route("/get_download_status")
def get_download_speed():
    """get download speed"""
    return (
        '{ "download_speed" : "'
        + format_byte(get_total_download_speed())
        + '/s" , "upload_speed" : "0.00 B/s" } '
    )


@_flask_app.route("/get_download_list")
def get_download_list():
    """get download list"""
    if request.args.get("already_down") is None:
        return "[]"

    already_down = request.args.get("already_down") == "true"

    download_result = get_download_result()
    result = "["
    for idx, value in download_result.items():
        is_already_down = value["down_byte"] == value["total_size"]

        if already_down and not is_already_down:
            continue

        if result != "[":
            result += ","
        download_speed = format_byte(value["download_speed"]) + "/s"
        result += (
            '{ "id":"'
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
