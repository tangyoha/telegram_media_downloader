"""Downloads media from telegram."""
import asyncio
import logging
import os
from datetime import datetime as dt
from typing import List, Optional, Tuple, Union

import pyrogram
import yaml
from pyrogram.types import Audio, Document, Photo, Video, VideoNote, Voice
from rich.logging import RichHandler

from utils.file_management import get_next_name, manage_duplicate_file
from utils.log import LogFilter
from utils.meta import print_meta
from utils.updates import check_for_updates

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)
logging.getLogger("pyrogram.session.session").addFilter(LogFilter())
logging.getLogger("pyrogram.client").addFilter(LogFilter())
logger = logging.getLogger("media_downloader")

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FAILED_IDS: list = []
DOWNLOADED_IDS: list = []


def update_config(config: dict):
    """
    Update existing configuration file.

    Parameters
    ----------
    config: dict
        Configuration to be written into config file.
    """
    config["ids_to_retry"] = (
        list(set(config["ids_to_retry"]) - set(DOWNLOADED_IDS)) + FAILED_IDS
    )
    with open("config.yaml", "w") as yaml_file:
        yaml.dump(config, yaml_file, default_flow_style=False)
    logger.info("Updated last read message_id to config file")


def _can_download(
    _type: str, file_formats: dict, file_format: Optional[str]
) -> bool:
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


async def _get_media_meta(
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

    if _type in ["voice", "video_note"]:
        # pylint: disable = C0209
        file_format = media_obj.mime_type.split("/")[-1]  # type: ignore
        file_name: str = os.path.join(
            THIS_DIR,
            _type,
            "{}_{}.{}".format(
                _type,
                dt.utcfromtimestamp(media_obj.date).isoformat(),  # type: ignore
                file_format,
            ),
        )
    else:
        file_name = os.path.join(
            THIS_DIR, _type, getattr(media_obj, "file_name", None) or ""
        )
    return file_name, file_format


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
    for retry in range(3):
        try:
            if message.media is None:
                return message.message_id
            for _type in media_types:
                _media = getattr(message, _type, None)
                if _media is None:
                    continue
                file_name, file_format = await _get_media_meta(_media, _type)
                if _can_download(_type, file_formats, file_format):
                    if _is_exist(file_name):
                        file_name = get_next_name(file_name)
                        download_path = await client.download_media(
                            message, file_name=file_name
                        )
                        # pylint: disable = C0301
                        download_path = manage_duplicate_file(download_path)  # type: ignore
                    else:
                        download_path = await client.download_media(
                            message, file_name=file_name
                        )
                    if download_path:
                        logger.info("Media downloaded - %s", download_path)
                    DOWNLOADED_IDS.append(message.message_id)
            break
        except pyrogram.errors.exceptions.bad_request_400.BadRequest:
            logger.warning(
                "Message[%d]: file reference expired, refetching...",
                message.message_id,
            )
            message = await client.get_messages(  # type: ignore
                chat_id=message.chat.id,  # type: ignore
                message_ids=message.message_id,
            )
            if retry == 2:
                # pylint: disable = C0301
                logger.error(
                    "Message[%d]: file reference expired for 3 retries, download skipped.",
                    message.message_id,
                )
                FAILED_IDS.append(message.message_id)
        except TypeError:
            # pylint: disable = C0301
            logger.warning(
                "Timeout Error occurred when downloading Message[%d], retrying after 5 seconds",
                message.message_id,
            )
            await asyncio.sleep(5)
            if retry == 2:
                logger.error(
                    "Message[%d]: Timing out after 3 reties, download skipped.",
                    message.message_id,
                )
                FAILED_IDS.append(message.message_id)
        except Exception as e:
            # pylint: disable = C0301
            logger.error(
                "Message[%d]: could not be downloaded due to following exception:\n[%s].",
                message.message_id,
                e,
                exc_info=True,
            )
            FAILED_IDS.append(message.message_id)
            break
    return message.message_id


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

    last_message_id = max(message_ids)
    return last_message_id


async def begin_import(config: dict, pagination_limit: int) -> dict:
    """
    Create pyrogram client and initiate download.

    The pyrogram client is created using the ``api_id``, ``api_hash``
    from the config and iter through message offset on the
    ``last_message_id`` and the requested file_formats.

    Parameters
    ----------
    config: dict
        Dict containing the config to create pyrogram client.
    pagination_limit: int
        Number of message to download asynchronously as a batch.

    Returns
    -------
    dict
        Updated configuration to be written into config file.
    """
    client = pyrogram.Client(
        "media_downloader",
        api_id=config["api_id"],
        api_hash=config["api_hash"],
    )
    await client.start()
    last_read_message_id: int = config["last_read_message_id"]
    messages_iter = client.iter_history(
        config["chat_id"],
        offset_id=last_read_message_id,
        reverse=True,
    )
    messages_list: list = []
    pagination_count: int = 0
    if config["ids_to_retry"]:
        logger.info("Downloading files failed during last run...")
        skipped_messages: list = await client.get_messages(
            chat_id=config["chat_id"], message_ids=config["ids_to_retry"]
        )
        for message in skipped_messages:
            pagination_count += 1
            messages_list.append(message)

    async for message in messages_iter:  # type: ignore
        if pagination_count != pagination_limit:
            pagination_count += 1
            messages_list.append(message)
        else:
            last_read_message_id = await process_messages(
                client,
                messages_list,
                config["media_types"],
                config["file_formats"],
            )
            pagination_count = 0
            messages_list = []
            messages_list.append(message)
            config["last_read_message_id"] = last_read_message_id
            update_config(config)
    if messages_list:
        last_read_message_id = await process_messages(
            client,
            messages_list,
            config["media_types"],
            config["file_formats"],
        )

    await client.stop()
    config["last_read_message_id"] = last_read_message_id
    return config


def main():
    """Main function of the downloader."""
    with open(os.path.join(THIS_DIR, "config.yaml")) as f:
        config = yaml.safe_load(f)
    updated_config = asyncio.get_event_loop().run_until_complete(
        begin_import(config, pagination_limit=100)
    )
    if FAILED_IDS:
        logger.info(
            "Downloading of %d files failed. "
            "Failed message ids are added to config file.\n"
            "These files will be downloaded on the next run.",
            len(set(FAILED_IDS)),
        )
    update_config(updated_config)
    check_for_updates()


if __name__ == "__main__":
    print_meta(logger)
    main()
