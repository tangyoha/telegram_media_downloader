"""Downloads media from telegram."""
import asyncio
import logging
import os
import shutil
import threading
import time
from typing import List, Optional, Tuple, Union

import pyrogram
from loguru import logger
from pyrogram.types import Audio, Document, Photo, Video, VideoNote, Voice
from rich.logging import RichHandler

from module.app import Application, ChatDownloadConfig, DownloadStatus, DownloadTaskNode
from module.bot import start_download_bot, stop_download_bot
from module.pyrogram_extension import (
    get_extension,
    record_download_status,
    report_bot_status,
    set_max_concurrent_transmissions,
    upload_telegram_chat,
)
from module.web import get_flask_app, update_download_status
from utils.format import truncate_filename, validate_title
from utils.log import LogFilter
from utils.meta import print_meta
from utils.meta_data import MetaData
from utils.updates import check_for_updates

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)

CONFIG_NAME = "config.yaml"
DATA_FILE_NAME = "data.yaml"
APPLICATION_NAME = "media_downloader"
app = Application(CONFIG_NAME, DATA_FILE_NAME, APPLICATION_NAME)

logger.add(
    os.path.join(app.log_file_path, "tdl.log"),
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
)

queue: asyncio.Queue = asyncio.Queue()
RETRY_TIME_OUT = 1

logging.getLogger("pyrogram.session.session").addFilter(LogFilter())
logging.getLogger("pyrogram.client").addFilter(LogFilter())

logging.getLogger("pyrogram").setLevel(logging.WARNING)


def _check_download_finish(media_size: int, download_path: str, ui_file_name: str):
    """Check download task if finish

    Parameters
    ----------
    media_size: int
        The size of the downloaded resource
    download_path: str
        Resource download hold path
    ui_file_name: str
        Really show file name

    """
    download_size = os.path.getsize(download_path)
    if media_size == download_size:
        logger.success("Media downloaded - {}", ui_file_name)
    else:
        logger.warning("Media downloaded with wrong size - {}", ui_file_name)
        os.remove(download_path)
        raise pyrogram.errors.exceptions.bad_request_400.BadRequest()


def _move_to_download_path(temp_download_path: str, download_path: str):
    """Move file to download path

    Parameters
    ----------
    temp_download_path: str
        Temporary download path

    download_path: str
        Download path

    """

    directory, _ = os.path.split(download_path)
    os.makedirs(directory, exist_ok=True)
    shutil.move(temp_download_path, download_path)


def _check_timeout(retry: int, _: int):
    """Check if message download timeout, then add message id into failed_ids

    Parameters
    ----------
    retry: int
        Retry download message times

    message_id: int
        Try to download message 's id

    """
    if retry == 2:
        return True
    return False


def _can_download(_type: str, file_formats: dict, file_format: Optional[str]) -> bool:
    """
    Check if the given file format can be downloaded.

    Parameters
    ----------
    _type: str
        Type of media object.
    file_formats: dict
        Dictionary containing the list of file_formats
        to be downloaded for `audio`, `document` & `video`
        media types
    file_format: str
        Format of the current file to be downloaded.

    Returns
    -------
    bool
        True if the file format can be downloaded else False.
    """
    if _type in ["audio", "document", "video"]:
        allowed_formats: list = file_formats[_type]
        if not file_format in allowed_formats and allowed_formats[0] != "all":
            return False
    return True


def _is_exist(file_path: str) -> bool:
    """
    Check if a file exists and it is not a directory.

    Parameters
    ----------
    file_path: str
        Absolute path of the file to be checked.

    Returns
    -------
    bool
        True if the file exists else False.
    """
    return not os.path.isdir(file_path) and os.path.exists(file_path)


# pylint: disable = R0912


async def _get_media_meta(
    chat_id: Union[int, str],
    message: pyrogram.types.Message,
    media_obj: Union[Audio, Document, Photo, Video, VideoNote, Voice],
    _type: str,
) -> Tuple[str, str, Optional[str]]:
    """Extract file name and file id from media object.

    Parameters
    ----------
    media_obj: Union[Audio, Document, Photo, Video, VideoNote, Voice]
        Media object to be extracted.
    _type: str
        Type of media object.

    Returns
    -------
    Tuple[str, str, Optional[str]]
        file_name, file_format
    """
    if _type in ["audio", "document", "video"]:
        # pylint: disable = C0301
        file_format: Optional[str] = media_obj.mime_type.split("/")[-1]  # type: ignore
    else:
        file_format = None

    file_name = None
    temp_file_name = None
    dirname = validate_title(f"{chat_id}")
    if message.chat and message.chat.title:
        dirname = validate_title(f"{message.chat.title}")

    if message.date:
        datetime_dir_name = message.date.strftime("%Y_%m")
    else:
        datetime_dir_name = "0"

    if _type in ["voice", "video_note"]:
        # pylint: disable = C0209
        file_format = media_obj.mime_type.split("/")[-1]  # type: ignore
        file_save_path = app.get_file_save_path(_type, dirname, datetime_dir_name)
        file_name = "{} - {}_{}.{}".format(
            message.id,
            _type,
            media_obj.date.isoformat(),  # type: ignore
            file_format,
        )

        temp_file_name = os.path.join(app.temp_save_path, dirname, file_name)

        file_name = os.path.join(file_save_path, file_name)
    else:
        file_name = getattr(media_obj, "file_name", None)
        caption = getattr(message, "caption", None)

        file_name_suffix = ".unknown"
        if not file_name:
            file_name_suffix = get_extension(
                media_obj.file_id, getattr(media_obj, "mime_type", "")
            )
        else:
            # file_name = file_name.split(".")[0]
            _, file_name_without_suffix = os.path.split(os.path.normpath(file_name))
            file_name, file_name_suffix = os.path.splitext(file_name_without_suffix)

        if caption:
            caption = validate_title(caption)
            app.set_caption_name(chat_id, message.media_group_id, caption)
        else:
            caption = app.get_caption_name(chat_id, message.media_group_id)

        if not file_name and message.photo:
            file_name = f"{message.photo.file_unique_id}"

        gen_file_name = (
            app.get_file_name(message.id, file_name, caption) + file_name_suffix
        )

        file_save_path = app.get_file_save_path(_type, dirname, datetime_dir_name)

        temp_file_name = os.path.join(app.temp_save_path, dirname, gen_file_name)

        file_name = os.path.join(file_save_path, gen_file_name)
    return truncate_filename(file_name), truncate_filename(temp_file_name), file_format


# pylint: disable = R0915,R0914


@record_download_status
async def download_media(
    client: pyrogram.client.Client,
    message: pyrogram.types.Message,
    media_types: List[str],
    file_formats: dict,
    chat_id: Union[int, str],
):
    """
    Download media from Telegram.

    Each of the files to download are retried 3 times with a
    delay of 5 seconds each.

    Parameters
    ----------
    client: pyrogram.client.Client
        Client to interact with Telegram APIs.
    message: pyrogram.types.Message
        Message object retrieved from telegram.
    media_types: list
        List of strings of media types to be downloaded.
        Ex : `["audio", "photo"]`
        Supported formats:
            * audio
            * document
            * photo
            * video
            * voice
    file_formats: dict
        Dictionary containing the list of file_formats
        to be downloaded for `audio`, `document` & `video`
        media types.

    Returns
    -------
    int
        Current message id.
    """

    # pylint: disable = R0912

    file_name: str = ""
    ui_file_name: str = ""
    task_start_time: float = time.time()
    media_size = 0
    _media = None
    try:
        for _type in media_types:
            _media = getattr(message, _type, None)
            if _media is None:
                continue
            file_name, temp_file_name, file_format = await _get_media_meta(
                chat_id, message, _media, _type
            )
            media_size = getattr(_media, "file_size", 0)

            ui_file_name = file_name
            if app.hide_file_name:
                ui_file_name = f"****{os.path.splitext(file_name)[-1]}"

            if _can_download(_type, file_formats, file_format):
                if _is_exist(file_name):

                    file_size = os.path.getsize(file_name)
                    if file_size or file_size == media_size:
                        logger.info(
                            "id={} {} already download,download skipped.\n",
                            message.id,
                            ui_file_name,
                        )
                        return DownloadStatus.SkipDownload, None
            else:
                return DownloadStatus.SkipDownload, None

            break
    except Exception as e:
        logger.error(
            "Message[{}]: could not be downloaded due to following exception:\n[{}].",
            message.id,
            e,
            exc_info=True,
        )
        return DownloadStatus.FailedDownload, None
    if _media is None:
        return DownloadStatus.SkipDownload, None

    message_id = message.id

    for retry in range(3):
        try:
            temp_download_path = await client.download_media(
                message,
                file_name=temp_file_name,
                progress=lambda down_byte, total_byte: update_download_status(
                    chat_id,
                    message_id,
                    down_byte,
                    total_byte,
                    ui_file_name,
                    task_start_time,
                ),
            )

            if temp_download_path and isinstance(temp_download_path, str):
                _move_to_download_path(temp_download_path, file_name)
                # TODO: if not exist file size or media
                _check_download_finish(media_size, file_name, ui_file_name)
                return DownloadStatus.SuccessDownload, file_name
        except pyrogram.errors.exceptions.bad_request_400.BadRequest:
            logger.warning(
                "Message[{}]: file reference expired, refetching...",
                message.id,
            )
            await asyncio.sleep(RETRY_TIME_OUT)
            message = await client.get_messages(  # type: ignore
                chat_id=message.chat.id,  # type: ignore
                message_ids=message.id,
            )
            if _check_timeout(retry, message.id):
                # pylint: disable = C0301
                logger.error(
                    "Message[{}]: file reference expired for 3 retries, download skipped.",
                    message.id,
                )
        except pyrogram.errors.exceptions.flood_420.FloodWait as wait_err:
            await asyncio.sleep(wait_err.value)
            logger.warning("Message[{}]: FlowWait {}", message.id, wait_err.value)
            _check_timeout(retry, message.id)
        except TypeError:
            # pylint: disable = C0301
            logger.warning(
                "Timeout Error occurred when downloading Message[{}], retrying after 5 seconds",
                message.id,
            )
            await asyncio.sleep(RETRY_TIME_OUT)
            if _check_timeout(retry, message.id):
                logger.error(
                    "Message[{}]: Timing out after 3 reties, download skipped.",
                    message.id,
                )
        except Exception as e:
            # pylint: disable = C0301
            logger.error(
                "Message[{}]: could not be downloaded due to following exception:\n[{}].",
                message.id,
                e,
                exc_info=True,
            )
            break

    return DownloadStatus.FailedDownload, None


def _load_config():
    """Load config"""
    app.load_config()


def _check_config() -> bool:
    """Check config"""
    print_meta(logger)
    try:
        _load_config()
    except Exception as e:
        logger.exception(f"load config error: {e}")
        return False

    return True


async def worker(client: pyrogram.client.Client):
    """Work for download task"""
    while app.is_running:
        try:
            item = await queue.get()
            message = item[0]
            bot: pyrogram.Client = item[1]
            node: DownloadTaskNode = item[2]
            download_status, file_name = await download_media(
                client, message, app.media_types, app.file_formats, node.chat_id
            )

            if not bot:
                app.set_download_id(node.chat_id, message.id, download_status)
            elif node.reply_message_id:
                await report_bot_status(bot, node, message, download_status)

            # upload telegram
            if node.upload_telegram_chat_id:
                if download_status is DownloadStatus.SuccessDownload:
                    await upload_telegram_chat(
                        client, node.upload_telegram_chat_id, message, file_name
                    )
                    if app.after_upload_telegram_delete:
                        os.remove(file_name)

                # forward text
                if (
                    download_status is DownloadStatus.SkipDownload
                    and message.text
                    and bot
                ):
                    await upload_telegram_chat(
                        client, node.upload_telegram_chat_id, message, file_name
                    )

            # rclone upload
            if (
                not node.upload_telegram_chat_id
                and download_status is DownloadStatus.SuccessDownload
            ):
                await app.upload_file(file_name)
        except Exception as e:
            logger.exception(f"{e}")


async def download_task(
    client: pyrogram.Client,
    chat_download_config: ChatDownloadConfig,
    node: DownloadTaskNode,
    limit: int = 0,
    bot: pyrogram.Client = None,
):
    """Download all task"""
    messages_iter = client.get_chat_history(
        node.chat_id,
        limit=limit,
        offset_id=chat_download_config.last_read_message_id,
        reverse=True,
    )
    if chat_download_config.ids_to_retry:
        logger.info("Downloading files failed during last run...")
        skipped_messages: list = await client.get_messages(  # type: ignore
            chat_id=node.chat_id, message_ids=chat_download_config.ids_to_retry
        )

        for message in skipped_messages:
            await queue.put((message, bot, node))
            chat_download_config.total_task += 1

    async for message in messages_iter:  # type: ignore
        meta_data = MetaData()

        caption = message.caption
        if caption:
            caption = validate_title(caption)
            app.set_caption_name(node.chat_id, message.media_group_id, caption)
        else:
            caption = app.get_caption_name(node.chat_id, message.media_group_id)
        meta_data.get_meta_data(message)
        meta_data.message_caption = caption

        if not app.need_skip_message(chat_download_config, message.id, meta_data):
            await queue.put((message, bot, node))
            chat_download_config.total_task += 1
        else:
            chat_download_config.downloaded_ids.append(message.id)

    chat_download_config.need_check = True


async def download_all_chat(client: pyrogram.Client):
    """Download All chat"""
    for key, value in app.chat_download_config.items():
        node = DownloadTaskNode(chat_id=key)
        await download_task(client, value, node)


async def run_until_all_task_finish():
    """Normal download"""
    while True:
        finish: bool = True
        for _, value in app.chat_download_config.items():
            if not value.need_check or value.total_task != value.finish_task:
                finish = False

        if finish:
            break

        await asyncio.sleep(1)


def _exec_loop():
    """Exec loop"""

    if app.bot_token:
        app.loop.run_forever()
    else:
        app.loop.run_until_complete(run_until_all_task_finish())


def main():
    """Main function of the downloader."""
    tasks = []
    client = pyrogram.Client(
        "media_downloader",
        api_id=app.api_id,
        api_hash=app.api_hash,
        proxy=app.proxy,
    )
    try:
        app.pre_run()
        threading.Thread(
            target=get_flask_app().run, daemon=True, args=(app.web_host, app.web_port)
        ).start()

        set_max_concurrent_transmissions(client, app.max_concurrent_transmissions)

        client.start()
        print("Successfully started (Press Ctrl+C to stop)")

        if app.bot_token:
            app.loop.create_task(
                start_download_bot(app, client, download_media, download_task)
            )

        app.loop.create_task(download_all_chat(client))
        for _ in range(app.max_download_task):
            task = app.loop.create_task(worker(client))
            tasks.append(task)

        _exec_loop()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt!")
    except Exception as e:
        logger.exception("{}", e)
    finally:
        client.stop()
        app.is_running = False
        for task in tasks:
            task.cancel()
        print("Stopped!")
        check_for_updates()
        logger.info("update config......")
        app.update_config()
        if app.bot_token:
            stop_download_bot()
        logger.success(
            "Updated last read message_id to config file,"
            "total download {}, total upload file {}",
            app.total_download_task,
            app.cloud_drive_config.total_upload_success_file_count,
        )


if __name__ == "__main__":
    if _check_config():
        main()
