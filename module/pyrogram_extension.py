"""Pyrogram ext"""

import asyncio
import os
import secrets
import struct
import time
from functools import wraps
from io import BytesIO, StringIO
from mimetypes import MimeTypes
from typing import List, Optional, Union

import pyrogram
from loguru import logger
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

from module.app import Application, DownloadStatus, ForwardStatus, TaskNode
from module.download_stat import get_download_result
from module.language import Language, _t
from utils.format import create_progress_bar, format_byte, truncate_filename
from utils.meta_data import MetaData

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


def get_extension(file_id: str, mime_type: str, dot: bool = True) -> str:
    """Get extension"""

    if not file_id:
        if dot:
            return ".unknown"
        return "unknown"

    file_type = _get_file_type(file_id)

    guessed_extension = _guess_extension(mime_type)

    if file_type in PHOTO_TYPES:
        extension = "jpg"
    elif file_type == FileType.VOICE:
        extension = guessed_extension or "ogg"
    elif file_type in (FileType.VIDEO, FileType.ANIMATION, FileType.VIDEO_NOTE):
        extension = guessed_extension or "mp4"
    elif file_type == FileType.DOCUMENT:
        extension = guessed_extension or "zip"
    elif file_type == FileType.STICKER:
        extension = guessed_extension or "webp"
    elif file_type == FileType.AUDIO:
        extension = guessed_extension or "mp3"
    else:
        extension = "unknown"

    if dot:
        extension = "." + extension
    return extension


async def send_message_by_language(
    client: pyrogram.client.Client,
    language: Language,
    chat_id: Union[int, str],
    reply_to_message_id: int,
    language_str: List[str],
):
    """Record download status"""
    msg = language_str[language.value - 1]

    return await client.send_message(
        chat_id, msg, reply_to_message_id=reply_to_message_id
    )


async def download_thumbnail(
    client: pyrogram.Client,
    temp_path: str,
    message: pyrogram.types.Message,
):
    """Downloads the thumbnail of a video message to a temporary file.

    Args:
        client: A Pyrogram client instance.
        temp_path: The path to a temporary directory where the thumbnail file
                   will be stored.
        message: A Pyrogram Message object representing the video message.

    Returns:
        A string representing the path of the thumbnail file, or None if the
        download failed.

    Raises:
        ValueError: If the downloaded thumbnail file size doesn't match the
                    expected file size.
    """
    thumbnail_file = None
    if message.video.thumbs:
        message = await fetch_message(client, message)
        thumbnail = message.video.thumbs[0] if message.video.thumbs else None
        unique_name = os.path.join(
            temp_path,
            "thumbnail",
            f"thumb-{int(time.time())}-{secrets.token_hex(8)}.jpg",
        )

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                thumbnail_file = await client.download_media(
                    thumbnail, file_name=unique_name
                )

                if os.path.getsize(thumbnail_file) == thumbnail.file_size:
                    break

                raise ValueError(
                    f"Thumbnail file size is {os.path.getsize(thumbnail_file)}"
                    f" bytes, actual {thumbnail.file_size}: {thumbnail_file}"
                )

            except Exception as e:
                if attempt == max_attempts:
                    logger.exception(
                        f"Failed to download thumbnail after {max_attempts}"
                        f" attempts: {e}"
                    )
                else:
                    message = await fetch_message(client, message)
                    logger.warning(
                        f"Attempt {attempt} to download thumbnail failed: {e}"
                    )
                    # Wait 2 seconds before retrying
                    await asyncio.sleep(2)

                thumbnail = None
                thumbnail_file = None
    return thumbnail_file


async def upload_telegram_chat(
    client: pyrogram.Client,
    upload_user: pyrogram.Client,
    app: Application,
    node: TaskNode,
    message: pyrogram.types.Message,
    file_name: str,
    download_status: DownloadStatus,
):
    """Upload telegram chat"""
    # upload telegram
    forward_ret = ForwardStatus.FailedForward
    if node.upload_telegram_chat_id:
        if download_status is DownloadStatus.SkipDownload:
            forward_ret = ForwardStatus.SkipForward
        elif download_status is DownloadStatus.SuccessDownload:
            try:
                forward_ret = await upload_telegram_chat_message(
                    client,
                    upload_user,
                    app,
                    node.upload_telegram_chat_id,
                    message,
                    file_name,
                )
            except Exception as e:
                logger.exception(f"Upload file {file_name} error: {e}")
            finally:
                if app.after_upload_telegram_delete:
                    os.remove(file_name)

            # forward text
            # FIXME: fix upload text
            # if (
            #     download_status is DownloadStatus.SkipDownload
            #     and message.text
            #     and bot
            # ):
            #     await upload_telegram_chat(
            #         client, app, node.upload_telegram_chat_id, message, file_name
            #     )
        node.stat_forward(forward_ret)


async def upload_telegram_chat_message(
    client: pyrogram.Client,
    upload_user: pyrogram.Client,
    app: Application,
    upload_telegram_chat_id: Union[int, str],
    message: pyrogram.types.Message,
    file_name: str,
) -> ForwardStatus:
    """See upload telegram_chat"""
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            await _upload_telegram_chat_message(
                client, upload_user, app, upload_telegram_chat_id, message, file_name
            )
            return ForwardStatus.SuccessForward
        except pyrogram.errors.exceptions.flood_420.FloodWait as wait_err:
            await asyncio.sleep(wait_err.value * 2)
            logger.warning(
                "Upload Message[{}]: FlowWait {}", message.id, wait_err.value
            )
            if attempt == max_attempts:
                return ForwardStatus.FailedForward

    return ForwardStatus.FailedForward


async def _upload_telegram_chat_message(
    client: pyrogram.Client,
    upload_user: pyrogram.Client,
    app: Application,
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
        # Download thumbnail
        thumbnail_file = await download_thumbnail(client, app.temp_save_path, message)
        try:
            # TODO(tangyoha): add more log when upload video more than 2000MB failed
            # Send video to the destination chat
            await upload_user.send_video(
                chat_id=upload_telegram_chat_id,
                video=file_name,
                thumb=thumbnail_file,
                width=message.video.width,
                height=message.video.height,
                duration=message.video.duration,
                caption=message.caption or "",
                parse_mode=pyrogram.enums.ParseMode.HTML,
            )
        except Exception as e:
            raise e
        finally:
            if thumbnail_file:
                os.remove(str(thumbnail_file))

    elif message.photo:
        await upload_user.send_photo(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.document:
        await upload_user.send_document(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.voice:
        await upload_user.send_voice(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.video_note:
        await upload_user.send_video_note(
            upload_telegram_chat_id, file_name, caption=message.caption
        )
    elif message.text:
        await upload_user.send_message(upload_telegram_chat_id, message.text)


def record_download_status(func):
    """Record download status"""

    @wraps(func)
    async def inner(
        client: pyrogram.client.Client,
        message: pyrogram.types.Message,
        media_types: List[str],
        file_formats: dict,
        node: TaskNode,
    ):
        if _download_cache[(node.chat_id, message.id)] is DownloadStatus.Downloading:
            return DownloadStatus.Downloading, None

        _download_cache[(node.chat_id, message.id)] = DownloadStatus.Downloading

        status, file_name = await func(client, message, media_types, file_formats, node)

        _download_cache[(node.chat_id, message.id)] = status

        return status, file_name

    return inner


async def report_bot_download_status(
    client: pyrogram.Client,
    node: TaskNode,
    download_status: DownloadStatus,
    download_size: int = 0,
):
    """
    Sends a message with the current status of the download bot.

    Parameters:
        client (pyrogram.Client): The client instance.
        node (TaskNode): The download task node.
        download_status (DownloadStatus): The current download status.

    Returns:
        None
    """
    node.stat(download_status)
    node.total_download_byte += download_size
    await report_bot_status(client, node)


async def report_bot_forward_status(
    client: pyrogram.Client,
    node: TaskNode,
    status: ForwardStatus,
):
    """
    Sends a message with the current status of the download bot.

    Parameters:
        client (pyrogram.Client): The client instance.
        node (TaskNode): The download task node.
        status (ForwardStatus): The current forward status.

    Returns:
        None
    """
    node.stat_forward(status)
    await report_bot_status(client, node)


async def report_bot_status(
    client: pyrogram.Client,
    node: TaskNode,
    immediate_reply=False,
):
    """
    Sends a message with the current status of the download bot.

    Parameters:
        client (pyrogram.Client): The client instance.
        node (TaskNode): The download task node.
        immediate_reply(bool): Immediate reply

    Returns:
        None
    """
    if not node.reply_message_id or not node.bot:
        return

    if immediate_reply or node.can_reply():
        if node.upload_telegram_chat_id:
            node.forward_msg_detail_str = (
                f"\n📥 {_t('Forward')}\n"
                f"├─ 📁 {_t('Total')}: {node.total_forward_task}\n"
                f"├─ ✅ {_t('Success')}: {node.success_forward_task}\n"
                f"├─ ❌ {_t('Failed')}: {node.failed_forward_task}\n"
                f"└─ ⏩ {_t('Skipped')}: {node.skip_forward_task}\n"
            )

        upload_msg_detail_str: str = ""

        if node.upload_success_count:
            upload_msg_detail_str = (
                f"\n📥 {_t('Upload')}\n"
                f"└─ ✅ {_t('Success')}: {node.upload_success_count}\n"
            )

        download_result_str = ""
        download_result = get_download_result()
        if node.chat_id in download_result:
            messages = download_result[node.chat_id]
            for idx, value in messages.items():
                task_id = value["task_id"]
                if task_id != node.task_id or value["down_byte"] == value["total_size"]:
                    continue

                temp_file_name = truncate_filename(
                    os.path.basename(value["file_name"]), 10
                )
                progress = int(value["down_byte"] / value["total_size"] * 100)
                download_result_str += (
                    f" ├─ 🆔 {_t('Message ID')}: {idx}\n"
                    f" │   ├─ 📁 : {temp_file_name}\n"
                    f" │   ├─ 📏 : {format_byte(value['total_size'])}\n"
                    f" │   ├─ 🚀 : {format_byte(value['download_speed'])}/s\n"
                    f" │   └─ 📊 : [{create_progress_bar(progress)}]"
                    f" ({progress}%)\n"
                )

            if download_result_str:
                download_result_str = "\n📈 Download Progresses:\n" + download_result_str

        new_msg_str = (
            f"```\n"
            f"🆔 task id: {node.task_id}\n"
            f"📥 {_t('Downloading')}: {format_byte(node.total_download_byte)}\n"
            f"├─ 📁 {_t('Total')}: {node.total_download_task}\n"
            f"├─ ✅ {_t('Success')}: {node.success_download_task}\n"
            f"├─ ❌ {_t('Failed')}: {node.failed_download_task}\n"
            f"└─ ⏩ {_t('Skipped')}: {node.skip_download_task}\n"
            f"{node.forward_msg_detail_str}"
            f"{upload_msg_detail_str}"
            f"{download_result_str}\n```"
        )

        try:
            if new_msg_str != node.last_edit_msg:
                await client.edit_message_text(
                    node.from_user_id,
                    node.reply_message_id,
                    new_msg_str,
                    parse_mode=pyrogram.enums.ParseMode.MARKDOWN,
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


async def fetch_message(client: pyrogram.Client, message: pyrogram.types.Message):
    """
    This function retrieves a message from a specified chat using the Pyrogram library.
     Args:
        client (pyrogram.Client): A client instance created using Pyrogram.
        message (pyrogram.types.Message): A message instance returned from Pyrogram.
     Returns:
        pyrogram.types.Message: A message object retrieved from the specified chat.
    """
    return await client.get_messages(
        chat_id=message.chat.id,
        message_ids=message.id,
    )


async def get_message_with_retry(
    client: pyrogram.Client,
    chat_id: Union[int, str],
    message_id: int,
    max_attempts: int = 3,
    wait_second: int = 15,
):
    """
    This function retrieves a message from a specified chat using the Pyrogram library.
     Args:
        client (pyrogram.Client): A client instance created using Pyrogram.
        chat_id (Union[int, str]): Chat Id
        message_id (int): message id.
     Returns:
        pyrogram.types.Message: A message object retrieved from the specified chat.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await client.get_messages(
                chat_id=chat_id,
                message_ids=message_id,
            )
        except Exception as e:
            if attempt == max_attempts:
                logger.error("Failed Get Message[{}]", message_id)
                return None

            logger.exception("Get Message[{}]: Error {}", message_id, e)
            await asyncio.sleep(wait_second)


async def check_user_permission(
    client: pyrogram.Client, user_id: Union[int, str], chat_id: Union[int, str]
) -> bool:
    """
    Check if the user has permission to send videos in the group.

    Args:
        client (pyrogram.Client): A client instance created using Pyrogram.
        user_id (Union[int, str]): User Id
        chat_id (Union[int, str]): Chat Id

     Returns:
        if can_send_media_messages return True
    """
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member and (
            not member.permissions or member.permissions.can_send_media_messages
        )
    except Exception:
        # logger.exception(e)
        pass

    return False


def set_meta_data(
    meta_data: MetaData, message: pyrogram.types.Message, caption: str = None
):
    """Get all meta data"""
    # message
    meta_data.message_date = getattr(message, "date", None)
    if caption:
        meta_data.message_caption = caption
    else:
        meta_data.message_caption = getattr(message, "caption", None) or ""
    meta_data.message_id = getattr(message, "id", None)

    from_user = getattr(message, "from_user")
    meta_data.sender_id = from_user.id if from_user else 0
    meta_data.sender_name = (from_user.username if from_user else "") or ""
    meta_data.reply_to_message_id = getattr(
        message, "reply_to_message_id", 1
    )  # 1 for General

    # media
    for kind in meta_data.AVAILABLE_MEDIA:
        media_obj = getattr(message, kind, None)
        if media_obj is not None:
            meta_data.media_type = kind
            break
    else:
        return
    meta_data.media_file_name = getattr(media_obj, "file_name", None) or ""
    meta_data.media_file_size = getattr(media_obj, "file_size", None)
    meta_data.media_width = getattr(media_obj, "width", None)
    meta_data.media_height = getattr(media_obj, "height", None)
    meta_data.media_duration = getattr(media_obj, "duration", None)
    meta_data.file_extension = get_extension(
        media_obj.file_id, getattr(media_obj, "mime_type", ""), False
    )
