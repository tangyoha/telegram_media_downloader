"""Downloads media from telegram."""
import asyncio
import logging
import os
import re
import threading
import time
from typing import List, Optional, Tuple, Union

import pyrogram
from loguru import logger
from pyrogram.types import Audio, Document, Photo, Video, VideoNote, Voice
from rich.logging import RichHandler

from module.app import Application
from module.pyrogram_extension import get_extension
from module.web import get_flask_app, update_download_status
from utils.format import truncate_filename
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

RETRY_TIME_OUT = 5

logging.getLogger("pyrogram.session.session").addFilter(LogFilter())
logging.getLogger("pyrogram.client").addFilter(LogFilter())

logging.getLogger("pyrogram").setLevel(logging.WARNING)


def _check_download_finish(
    media_size: int, download_path: str, ui_file_name: str, message_id: int
):
    """Check download task if finish

    Parameters
    ----------
    media_size: int
        The size of the downloaded resource
    download_path: str
        Resource download hold path
    ui_file_name: str
        Really show file name
    message_id: int
        Download message id

    """
    download_size = os.path.getsize(download_path)
    if media_size == download_size:
        logger.success("Media downloaded - {}", ui_file_name)
        app.downloaded_ids.append(message_id)
        app.total_download_task += 1
    else:
        logger.error("Media downloaded with wrong size - {}", ui_file_name)
        os.remove(download_path)
        raise TypeError("Media downloaded with wrong size")


def _check_timeout(retry: int, message_id: int):
    """Check if message download timeout, then add message id into failed_ids

    Parameters
    ----------
    retry: int
        Retry download message times

    message_id: int
        Try to download message 's id

    """
    if retry == 2:
        app.failed_ids.append(message_id)
        return True
    return False


def _validate_title(title: str):
    """Fix if title validation fails

    Parameters
    ----------
    title: str
        Chat title

    """

    r_str = r"[\//\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    new_title = re.sub(r_str, "_", title)
    return new_title


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
    message: pyrogram.types.Message,
    media_obj: Union[Audio, Document, Photo, Video, VideoNote, Voice],
    _type: str,
) -> Tuple[str, Optional[str]]:
    """Extract file name and file id from media object.

    Parameters
    ----------
    media_obj: Union[Audio, Document, Photo, Video, VideoNote, Voice]
        Media object to be extracted.
    _type: str
        Type of media object.

    Returns
    -------
    Tuple[str, Optional[str]]
        file_name, file_format
    """
    if _type in ["audio", "document", "video"]:
        # pylint: disable = C0301
        file_format: Optional[str] = media_obj.mime_type.split("/")[-1]  # type: ignore
    else:
        file_format = None

    file_name = None
    dirname = _validate_title(f"{app.chat_id}")
    if message.chat and message.chat.title:
        dirname = _validate_title(f"{message.chat.title}")

    if message.date:
        datetime_dir_name = message.date.strftime("%Y_%m")
    else:
        datetime_dir_name = "0"

    if _type in ["voice", "video_note"]:
        # pylint: disable = C0209
        file_format = media_obj.mime_type.split("/")[-1]  # type: ignore
        file_save_path = app.get_file_save_path(_type, dirname, datetime_dir_name)

        file_name = os.path.join(
            file_save_path,
            "{} - {}_{}.{}".format(
                message.id,
                _type,
                media_obj.date.isoformat(),  # type: ignore
                file_format,
            ),
        )
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
            caption = _validate_title(caption)
            app.set_caption_name(app.chat_id, message.media_group_id, caption)
        else:
            caption = app.get_caption_name(app.chat_id, message.media_group_id)

        if not file_name and message.photo:
            file_name = f"{message.photo.file_unique_id}"

        gen_file_name = (
            app.get_file_name(message.id, file_name, caption) + file_name_suffix
        )

        file_save_path = app.get_file_save_path(_type, dirname, datetime_dir_name)
        file_name = os.path.join(file_save_path, gen_file_name)
        file_name = truncate_filename(file_name)
    return file_name, file_format


# pylint: disable = R0915
async def download_media(
    client: pyrogram.client.Client,
    message: pyrogram.types.Message,
    media_types: List[str],
    file_formats: dict,
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
        if message.media is None:
            return message.id
        for _type in media_types:
            _media = getattr(message, _type, None)
            if _media is None:
                continue
            file_name, file_format = await _get_media_meta(message, _media, _type)
            media_size = getattr(_media, "file_size", 0)

            ui_file_name = file_name
            if app.hide_file_name:
                ui_file_name = f"****{os.path.splitext(file_name)[-1]}"

            if _can_download(_type, file_formats, file_format):
                if _is_exist(file_name):
                    # TODO: check if the file download complete
                    # file_size = os.path.getsize(file_name)
                    # media_size = getattr(_media, 'file_size')
                    # if media_size is not None and file_size != media_size:

                    # FIXME: if exist and not empty file skip
                    logger.info(
                        "id={} {} already download,download skipped.\n",
                        message.id,
                        ui_file_name,
                    )

                    app.downloaded_ids.append(message.id)

                    return message.id

            break
    except Exception as e:
        logger.error(
            "Message[{}]: could not be downloaded due to following exception:\n[{}].",
            message.id,
            e,
            exc_info=True,
        )
        app.failed_ids.append(message.id)
        return message.id

    if _media is None:
        return message.id

    for retry in range(3):
        try:
            download_path = await client.download_media(
                message,
                file_name=file_name,
                progress=lambda down_byte, total_byte: update_download_status(
                    message.id,
                    down_byte,
                    total_byte,
                    ui_file_name,
                    task_start_time,
                ),
            )

            if download_path and isinstance(download_path, str):
                # TODO: if not exist file size or media
                _check_download_finish(
                    media_size, download_path, ui_file_name, message.id
                )
                await app.upload_file(file_name)

            break
        except pyrogram.errors.exceptions.bad_request_400.BadRequest:
            logger.warning(
                "Message[{}]: file reference expired, refetching...",
                message.id,
            )
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
            app.failed_ids.append(message.id)
            break
    return message.id


async def process_messages(
    client: pyrogram.client.Client,
    messages: List[pyrogram.types.Message],
    media_types: List[str],
    file_formats: dict,
) -> int:
    """
    Download media from Telegram.

    Parameters
    ----------
    client: pyrogram.client.Client
        Client to interact with Telegram APIs.
    messages: list
        List of telegram messages.
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
        Max value of list of message ids.
    """
    message_ids = await asyncio.gather(
        *[
            download_media(client, message, media_types, file_formats)
            for message in messages
        ]
    )

    last_message_id: int = max(message_ids)
    return last_message_id


async def begin_import(pagination_limit: int):
    """
    Create pyrogram client and initiate download.

    The pyrogram client is created using the ``api_id``, ``api_hash``
    from the config and iter through message offset on the
    ``last_message_id`` and the requested file_formats.

    Parameters
    ----------
    pagination_limit: int
        Number of message to download asynchronously as a batch.
    """
    client = pyrogram.Client(
        "media_downloader",
        api_id=app.api_id,
        api_hash=app.api_hash,
        proxy=app.proxy,
    )

    if getattr(client, "max_concurrent_transmissions", None):
        client.max_concurrent_transmissions = app.max_concurrent_transmissions

    await client.start()
    print("Successfully started (Press Ctrl+C to stop)")

    last_read_message_id: int = app.last_read_message_id
    messages_iter = client.get_chat_history(
        app.chat_id, offset_id=app.last_read_message_id, reverse=True
    )
    messages_list: list = []
    pagination_count: int = 0
    if app.ids_to_retry:
        logger.info("Downloading files failed during last run...")
        skipped_messages: list = await client.get_messages(  # type: ignore
            chat_id=app.chat_id, message_ids=app.ids_to_retry
        )
        for message in skipped_messages:
            if pagination_count != pagination_limit:
                pagination_count += 1
                messages_list.append(message)
            else:
                last_read_message_id = await process_messages(
                    client,
                    messages_list,
                    app.media_types,
                    app.file_formats,
                )
                pagination_count = 0
                messages_list = []
                messages_list.append(message)
                app.last_read_message_id = last_read_message_id

    async for message in messages_iter:  # type: ignore
        meta_data = MetaData()
        meta_data.get_meta_data(message)
        if pagination_count != pagination_limit:
            if not app.need_skip_message(str(app.chat_id), message.id, meta_data):
                pagination_count += 1
                messages_list.append(message)
        else:
            last_read_message_id = await process_messages(
                client,
                messages_list,
                app.media_types,
                app.file_formats,
            )
            pagination_count = 0
            messages_list = []
            messages_list.append(message)
            app.last_read_message_id = last_read_message_id
    if messages_list:
        last_read_message_id = await process_messages(
            client,
            messages_list,
            app.media_types,
            app.file_formats,
        )

    await client.stop()
    app.last_read_message_id = last_read_message_id


def main():
    """Main function of the downloader."""
    try:
        app.pre_run()
        threading.Thread(
            target=get_flask_app().run, daemon=True, args=(app.web_host, app.web_port)
        ).start()
        asyncio.get_event_loop().run_until_complete(begin_import(pagination_limit=10))
        if app.failed_ids:
            logger.error(
                "Downloading of {} files failed. "
                "Failed message ids are added to config file.\n"
                "These files will be downloaded on the next run.",
                len(set(app.failed_ids)),
            )
        check_for_updates()
    except KeyboardInterrupt:
        logger.info("Stopped!")
    except Exception as e:
        logger.exception("{}", e)
    finally:
        logger.info("update config......")
        app.update_config()
        logger.success(
            "Updated last read message_id to config file,"
            "total download {}, total upload file {}",
            app.total_download_task,
            app.cloud_drive_config.total_upload_success_file_count,
        )


def _load_config():
    """Load config"""
    app.load_config()


def _check_config() -> bool:
    """Check config"""
    print_meta(logger)
    try:
        _load_config()
    except Exception as e:
        logger.error(f"load config error: {e}")
        return False

    return True


if __name__ == "__main__":
    if _check_config():
        main()
