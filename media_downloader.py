"""Downloads media from telegram."""
import os
import logging
from typing import List, Tuple
from datetime import datetime as dt

import yaml
import pyrogram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

f = open(os.path.join(THIS_DIR, "config.yaml"))
config = yaml.safe_load(f)
f.close()


def _get_media_meta(
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
        file_id, file_name
    """
    file_id: str = media_obj.file_id
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
    return file_id, file_name


def download_media(
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
        file_id, file_name
    """
    messages = client.iter_history(
        chat_id, offset_id=last_read_message_id, reverse=True
    )
    last_id: int = 0
    for message in messages:
        if message.media:
            for _type in media_types:
                _media = getattr(message, _type, None)
                if _media:
                    file_id, file_name = _get_media_meta(_media, _type)
                    download_path = client.download_media(
                        file_id, file_name=file_name
                    )
                    logger.info("Media downloaded - %s", download_path)
        last_id = message.message_id
    return last_id


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


def begin_import():
    """Skeleton fucntion that creates client and import, write config"""
    client = pyrogram.Client(
        "media_downloader",
        api_id=config["api_id"],
        api_hash=config["api_hash"],
    )
    client.start()
    last_id = download_media(
        client,
        config["chat_id"],
        config["last_read_message_id"],
        config["media_types"],
    )
    client.stop()
    config["last_read_message_id"] = last_id + 1
    update_config(config)


if __name__ == "__main__":
    begin_import()
