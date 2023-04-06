"""Pyrogram ext"""

import asyncio
import struct
from functools import wraps
from io import BytesIO, StringIO
from mimetypes import MimeTypes
from typing import List, Optional, Union

import pyrogram
from pyrogram.client import Cache
from pyrogram.file_id import (
    FILE_REFERENCE_FLAG,
    PHOTO_TYPES,
    WEB_LOCATION_FLAG,
    FileType,
    b64_decode,
    rle_decode,
)
from pyrogram.mime_types import mime_types

from module.app import DownloadStatus, DownloadTaskNode

_mimetypes = MimeTypes()
_mimetypes.readfp(StringIO(mime_types))
_download_cache = Cache(1024 * 1024 * 1024)


def reset_download_cache():
    """Reset download cache"""
    _download_cache.store.clear()


def _guess_mime_type(filename: str) -> Optional[str]:
    """Guess mime type"""
    return _mimetypes.guess_type(filename)[0]


def _guess_extension(mime_type: str) -> Optional[str]:
    """Guess extension"""
    return _mimetypes.guess_extension(mime_type)


def _get_file_type(file_id: str):
    """Get file type"""
    decoded = rle_decode(b64_decode(file_id))

    # File id versioning. Major versions lower than 4 don't have a minor version
    major = decoded[-1]

    if major < 4:
        buffer = BytesIO(decoded[:-1])
    else:
        buffer = BytesIO(decoded[:-2])

    file_type, _ = struct.unpack("<ii", buffer.read(8))

    file_type &= ~WEB_LOCATION_FLAG
    file_type &= ~FILE_REFERENCE_FLAG

    try:
        file_type = FileType(file_type)
    except ValueError as exc:
        raise ValueError(f"Unknown file_type {file_type} of file_id {file_id}") from exc

    return file_type


def get_extension(file_id: str, mime_type: str) -> str:
    """Get extension"""

    file_type = _get_file_type(file_id)

    guessed_extension = _guess_extension(mime_type)

    if file_type in PHOTO_TYPES:
        extension = ".jpg"
    elif file_type == FileType.VOICE:
        extension = guessed_extension or ".ogg"
    elif file_type in (FileType.VIDEO, FileType.ANIMATION, FileType.VIDEO_NOTE):
        extension = guessed_extension or ".mp4"
    elif file_type == FileType.DOCUMENT:
        extension = guessed_extension or ".zip"
    elif file_type == FileType.STICKER:
        extension = guessed_extension or ".webp"
    elif file_type == FileType.AUDIO:
        extension = guessed_extension or ".mp3"
    else:
        extension = ".unknown"

    return extension


async def upload_telegram_chat(
    client: pyrogram.Client,
    upload_telegram_chat_id: Union[int, str],
    message: pyrogram.types.Message,
    file_name: str,
):
    """
    Uploads a video or message to a Telegram chat.

    Parameters:
        client (pyrogram.Client): The pyrogram client.
        upload_telegram_chat_id (Union[int, str]): The ID of the chat to upload to.
        message (pyrogram.types.Message): The message to upload.
        file_name (str): The name of the file to upload.
    """
    if message.video:
        await client.send_video(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.photo:
        await client.send_photo(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.document:
        await client.send_document(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.voice:
        await client.send_voice(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.video_note:
        await client.send_video_note(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.text:
        await client.send_message(upload_telegram_chat_id, message.text)


def record_download_status(func):
    """Record download status"""

    @wraps(func)
    async def inner(
        client: pyrogram.client.Client,
        message: pyrogram.types.Message,
        media_types: List[str],
        file_formats: dict,
        chat_id: Union[int, str],
    ):
        if _download_cache[(chat_id, message.id)] is DownloadStatus.Downloading:
            return DownloadStatus.Downloading, None

        _download_cache[(chat_id, message.id)] = DownloadStatus.Downloading

        status, file_name = await func(
            client, message, media_types, file_formats, chat_id
        )

        _download_cache[(chat_id, message.id)] = status

        return status, file_name

    return inner


async def report_bot_status(
    client: pyrogram.Client,
    node: DownloadTaskNode,
    message: pyrogram.types.Message,
    download_status: DownloadStatus,
):
    """
    Sends a message with the current status of the download bot.

    Parameters:
        client (pyrogram.Client): The client instance.
        node (DownloadTaskNode): The download task node.
        message (pyrogram.types.Message): The message object.
        download_status (DownloadStatus): The current download status.

    Returns:
        None
    """
    node.stat(download_status)
    if node.can_reply():
        new_msg_str = (
            f"{node.reply_message}\n"
            f"**total**: `{node.total_download_task}`\n"
            f"**success**: `{node.success_download_task}`\n"
            f"**failed**: `{node.failed_download_task}`\n"
            f"**skip**: `{node.skip_download_task}`\n"
            f"**status**:\n"
            f"  * message id : `{message.id}`\n"
            f"  * status: **{download_status.name}**"
        )

        try:
            if new_msg_str != node.last_edit_msg:
                await client.edit_message_text(
                    node.from_user_id, node.reply_message_id, new_msg_str
                )
        except Exception:
            pass


def set_max_concurrent_transmissions(
    client: pyrogram.Client, max_concurrent_transmissions: int
):
    """Set maximum concurrent transmissions"""
    if getattr(client, "max_concurrent_transmissions", None):
        client.max_concurrent_transmissions = max_concurrent_transmissions
        client.save_file_semaphore = asyncio.Semaphore(
            client.max_concurrent_transmissions
        )
        client.get_file_semaphore = asyncio.Semaphore(
            client.max_concurrent_transmissions
        )
