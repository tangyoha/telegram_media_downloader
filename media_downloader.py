"""Downloads media from telegram."""
import os
import logging
from typing import List, Tuple
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
) -> Tuple[str, str]:
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
        file_ref, file_name
    """
    file_ref: str = media_obj.file_ref
    if _type == "voice":
        file_format: str = media_obj.mime_type.split("/")[-1]
        file_name: str = os.path.join(
            THIS_DIR,
            _type,
            "voice_{}.{}".format(
                dt.utcfromtimestamp(media_obj.date).isoformat(), file_format
            ),
        )
    elif _type == "photo":
        file_name = os.path.join(THIS_DIR, _type, "")
    else:
        file_name = os.path.join(THIS_DIR, _type, media_obj.file_name)
    return file_ref, file_name


async def download_media(client, message, media_types):
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

    Returns
    -------
    integer
        message_id
    """
    if message.media:
        for _type in media_types:
            _media = getattr(message, _type, None)
            if _media:
                file_ref, file_name = await _get_media_meta(_media, _type)
                download_path = await client.download_media(
                    message, file_ref=file_ref, file_name=file_name
                )
                logger.info("Media downloaded - %s", download_path)
    return message.message_id


async def process_messages(
    client: pyrogram.client.client.Client,
    chat_id: str,
    last_read_message_id: int,
    media_types: List[str],
) -> int:
    """Download media from Telegram.

    Parameters
    ----------
    client: pyrogram.client.client.Client
        Client to interact with Telegram APIs.
    chat_id: string
        Id of the chat to download media from.
    last_read_message_id: integer
        Id of last message read from the conversational thread.
    media_types: list
        List of strings of media types to be downloaded.
        Ex : `["audio", "photo"]`
        Supported formats:
            * audio
            * document
            * photo
            * video
            * voice

    Returns
    -------
    integer
        last_message_id
    """
    message_ids = await asyncio.gather(
        *[
            download_media(client, message, media_types)
            async for message in client.iter_history(
                chat_id, offset_id=last_read_message_id, reverse=True
            )
        ]
    )

    last_message_id = max(message_ids, default=last_read_message_id)
    return last_message_id


async def begin_import(config):
    """Skeleton fucntion that creates client and import, write config"""
    client = pyrogram.Client(
        "media_downloader",
        api_id=config["api_id"],
        api_hash=config["api_hash"],
    )
    await client.start()
    last_read_message_id = await process_messages(
        client,
        config["chat_id"],
        config["last_read_message_id"],
        config["media_types"],
    )
    await client.stop()
    config["last_read_message_id"] = last_read_message_id + 1
    return config


if __name__ == "__main__":
    f = open(os.path.join(THIS_DIR, "config.yaml"))
    config = yaml.safe_load(f)
    f.close()
    updated_config = asyncio.get_event_loop().run_until_complete(
        begin_import(config)
    )
    update_config(updated_config)
