"""Downloads media from telegram."""
import os
import logging
from typing import List, Tuple, Optional
from datetime import datetime as dt

import asyncio
import yaml
import pyrogram


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def update_config(config: dict):
    """Update exisitng configuration file.

    Parameters
    ----------
    config: dictionary
        Configuraiton to be written into config file.
    """
    with open("config.yaml", "w") as yaml_file:
        yaml.dump(config, yaml_file, default_flow_style=False)
    logger.info("Updated last read message_id to config file")


async def _get_media_meta(
    media_obj: pyrogram.client.types.messages_and_media, _type: str
) -> Tuple[str, str, Optional[str]]:
    """Extract file name and file id.

    Parameters
    ----------
    media_obj: pyrogram.client.types.messages_and_media
        Media object to be extracted.
    _type: string
        Type of media object.

    Returns
    -------
    tuple
        file_ref, file_name, file_format
    """
    file_ref: str = media_obj.file_ref

    if _type in ["audio", "document", "video"]:
        file_format: Optional[str] = media_obj.mime_type.split("/")[-1]
    else:
        file_format = None

    if _type == "voice":
        file_format = media_obj.mime_type.split("/")[-1]
        file_name: str = os.path.join(
            THIS_DIR,
            _type,
            "voice_{}.{}".format(
                dt.utcfromtimestamp(media_obj.date).isoformat(), file_format
            ),
        )
    elif _type in ["photo", "video"]:
        file_name = os.path.join(THIS_DIR, _type, "")
    else:
        file_name = os.path.join(THIS_DIR, _type, media_obj.file_name)
    return file_ref, file_name, file_format


async def download_media(
    client: pyrogram.client.client.Client,
    message: pyrogram.Message,
    media_types: List[str],
    file_formats: dict,
):
    """Download media from Telegram.

    Parameters
    ----------
    client: pyrogram.client.client.Client
        Client to interact with Telegram APIs.
    message: pyrogram.Message
        Message object retrived from telegram.
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
        media types

    Returns
    -------
    integer
        message_id
    """

    def _can_download(_type, file_formats, file_format):
        if _type in ["audio", "document", "video"]:
            allowed_formats: list = file_formats[_type]
            if (
                not file_format in allowed_formats
                and allowed_formats[0] != "all"
            ):
                return False
        return True

    if message.media:
        for _type in media_types:
            _media = getattr(message, _type, None)
            if _media:
                file_ref, file_name, file_format = await _get_media_meta(
                    _media, _type
                )
                if _can_download(_type, file_formats, file_format):
                    download_path = await client.download_media(
                        message, file_ref=file_ref, file_name=file_name
                    )
                    logger.info("Media downloaded - %s", download_path)
    return message.message_id


async def process_messages(
    client: pyrogram.client.client.Client,
    messages: list,
    media_types: List[str],
    file_formats: dict,
) -> int:
    """Download media from Telegram.

    Parameters
    ----------
    client: pyrogram.client.client.Client
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
        media types
    Returns
    -------
    integer
        last_message_id
    """
    message_ids = await asyncio.gather(
        *[
            download_media(client, message, media_types, file_formats)
            for message in messages
        ]
    )

    last_message_id = max(message_ids)
    return last_message_id


async def begin_import(config: dict):
    """Skeleton fucntion that creates client and import, write config"""
    client = pyrogram.Client(
        "media_downloader",
        api_id=config["api_id"],
        api_hash=config["api_hash"],
    )
    await client.start()
    last_read_message_id: int = config["last_read_message_id"]
    messages_iter = client.iter_history(
        config["chat_id"], offset_id=last_read_message_id, reverse=True,
    )
    pagination_count: int = 0
    messages_list: list = []

    async for message in messages_iter:
        if not pagination_count == 100:
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


if __name__ == "__main__":
    f = open(os.path.join(THIS_DIR, "config.yaml"))
    config = yaml.safe_load(f)
    f.close()
    updated_config = asyncio.get_event_loop().run_until_complete(
        begin_import(config)
    )
    update_config(updated_config)
