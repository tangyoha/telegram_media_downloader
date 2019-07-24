import os
import logging

import yaml
from pyrogram import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

f = open(os.path.join(THIS_DIR, "config.yaml"))
config = yaml.safe_load(f)
f.close()


def download_media(client: Client, chat_id: str, last_read_message_id: int) -> int:
    messages = client.iter_history(
        chat_id, offset_id=last_read_message_id, reverse=True
    )
    last_id: int = 0
    for message in messages:
        if message.document:
            file_id: str = message.document.file_id
            file_name: str = os.path.join(
                THIS_DIR, "documents", message.document.file_name
            )
            download_path = client.download_media(file_id, file_name=file_name)
            logger.info("Document downloaded - %s", download_path)
            last_id = message.message_id
    return last_id


def update_config(config: dict):
    with open("config.yaml", "w") as yaml_file:
        yaml.dump(config, yaml_file, default_flow_style=False)
    logger.info("Updated last read message_id to config file")


def begin_import():
    client = Client(
        "document_downloader", api_id=config["api_id"], api_hash=config["api_hash"]
    )
    client.start()
    last_id = download_media(
        client, config["chat_id"] + 1, config["last_read_message_id"]
    )
    client.stop()
    config["last_read_message_id"] = last_id
    update_config(config)


if __name__ == "__main__":
    begin_import()
