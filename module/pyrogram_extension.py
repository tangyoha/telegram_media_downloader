"""Pyrogram ext"""

import asyncio
import os
import secrets
import struct
import time
from datetime import datetime
from functools import wraps
from io import BytesIO, StringIO
from mimetypes import MimeTypes
from typing import Callable, Iterable, List, Optional, Union

import pyrogram
from loguru import logger
from pyrogram import types, utils
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

from module.app import (
    Application,
    CloudDriveUploadStat,
    DownloadStatus,
    ForwardStatus,
    TaskNode,
    UploadProgressStat,
    UploadStatus,
)
from module.download_stat import get_download_result
from module.language import Language, _t
from module.send_media_group_v2 import cache_media, send_media_group_v2
from utils.format import (
    create_progress_bar,
    extract_info_from_link,
    format_byte,
    truncate_filename,
)
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


def get_media_obj(
    message: pyrogram.types.Message, media: str = None, caption: str = None
) -> Union[
    types.InputMediaPhoto,
    types.InputMediaVideo,
    types.InputMediaAudio,
    types.InputMediaDocument,
    types.InputMediaAnimation,
]:
    """Get media object"""
    media_type = message.media
    if media_type == pyrogram.enums.MessageMediaType.PHOTO:
        return types.InputMediaPhoto(media, caption=caption)

    if media_type == pyrogram.enums.MessageMediaType.VIDEO:
        return types.InputMediaVideo(
            media,
            caption=caption,
            width=message.video.width,
            height=message.video.height,
            duration=message.video.duration,
        )

    if media_type in [
        pyrogram.enums.MessageMediaType.AUDIO,
        pyrogram.enums.MessageMediaType.VOICE,
    ]:
        return types.InputMediaAudio(media, caption=caption)

    if media_type == pyrogram.enums.MessageMediaType.DOCUMENT:
        return types.InputMediaDocument(media, caption=caption)

    if media_type == pyrogram.enums.MessageMediaType.ANIMATION:
        return types.InputMediaAnimation(media, caption=caption)

    return None


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
    download_status: DownloadStatus,
    file_name: str = None,
):
    """Upload telegram chat"""
    # upload telegram
    if node.upload_telegram_chat_id:
        if download_status is DownloadStatus.SkipDownload and message.media:
            if message.media_group_id:
                await proc_cache_forward(client, node, message, True, app)
            return

        if download_status is DownloadStatus.SuccessDownload or (
            download_status is DownloadStatus.SkipDownload and not message.media
        ):
            try:
                await upload_telegram_chat_message(
                    client,
                    upload_user,
                    app,
                    node,
                    message,
                    file_name,
                )
            except Exception as e:
                logger.exception(f"Upload file {file_name} error: {e}")
            finally:
                if file_name and app.after_upload_telegram_delete:
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


async def upload_telegram_chat_message(
    client: pyrogram.Client,
    upload_user: pyrogram.Client,
    app: Application,
    node: TaskNode,
    message: pyrogram.types.Message,
    file_name: str = None,
) -> ForwardStatus:
    """See upload telegram_chat"""
    forward_status = ForwardStatus.FailedForward
    max_attempts = 3
    for _ in range(1, max_attempts + 1):
        try:
            forward_status = await _upload_telegram_chat_message(
                client, upload_user, app, node, message, file_name
            )
            break
        except pyrogram.errors.exceptions.flood_420.FloodWait as wait_err:
            await asyncio.sleep(wait_err.value * 2)
            logger.warning(
                "Upload Message[{}]: FlowWait {}", message.id, wait_err.value
            )
        except Exception as e:
            logger.exception(f"Upload file {file_name} error: {e}")
            return ForwardStatus.FailedForward

    if forward_status != ForwardStatus.CacheForward:
        node.stat_forward(forward_status)
    return forward_status


# pylint: disable=R0912
async def _upload_signal_message(
    client: pyrogram.Client,
    upload_user: pyrogram.Client,
    app: Application,
    node: TaskNode,
    upload_telegram_chat_id: Union[int, str, None],
    message: pyrogram.types.Message,
    file_name: Optional[str],
    caption: Optional[str] = None,
):
    """
    Uploads a video or message to a Telegram chat.

    Parameters:
        client (pyrogram.Client): The pyrogram client.
        upload_telegram_chat_id (Union[int, str]): The ID of the chat to upload to.
        message (pyrogram.types.Message): The message to upload.
        file_name (str): The name of the file to upload.
    """ 
    ui_file_name = file_name
    if file_name:
        ui_file_name = (
            f"****{os.path.splitext(file_name)[-1]}"
            if app.hide_file_name
            else file_name
        )

    if message.video:
        # Download thumbnail
        thumbnail_file = await download_thumbnail(client, app.temp_save_path, message)
        try:
            # TODO(tangyoha): add more log when upload video more than 2000MB failed
            # Send video to the destination chat
            if node.reply_to_message:
                await node.reply_to_message.reply_video(
                    file_name,
                    caption=caption,
                    message_thread_id=node.topic_id,
                    thumb=thumbnail_file,
                    width=message.video.width,
                    height=message.video.height,
                    duration=message.video.duration,
                    parse_mode=pyrogram.enums.ParseMode.HTML,
                )
            else:
                await upload_user.send_video(
                    upload_telegram_chat_id,
                    file_name,
                    thumb=thumbnail_file,
                    width=message.video.width,
                    height=message.video.height,
                    duration=message.video.duration,
                    caption=caption,
                    parse_mode=pyrogram.enums.ParseMode.HTML,
                    progress=update_upload_stat,
                    progress_args=(
                        message.id,
                        ui_file_name,
                        time.time(),
                        node,
                        upload_user,
                    ),
                    message_thread_id=node.topic_id,
                )
        except Exception as e:
            raise e
        finally:
            if thumbnail_file:
                os.remove(str(thumbnail_file))

    elif message.photo:
        if node.reply_to_message:
            await node.reply_to_message.reply_photo(
                file_name,
                caption=caption,
                message_thread_id=node.topic_id,
            )
        else:
            await upload_user.send_photo(
                upload_telegram_chat_id,
                file_name,
                caption=caption,
                progress=update_upload_stat,
                progress_args=(
                    message.id,
                    ui_file_name,
                    time.time(),
                    node,
                    upload_user,
                ),
                message_thread_id=node.topic_id,
            )
    elif message.document:
        if node.reply_to_message:
            await node.reply_to_message.reply_document(
                file_name,
                caption=caption,
                message_thread_id=node.topic_id,
            )
        else:
            await upload_user.send_document(
                upload_telegram_chat_id,
                file_name,
                caption=caption,
                progress=update_upload_stat,
                progress_args=(
                    message.id,
                    ui_file_name,
                    time.time(),
                    node,
                    upload_user,
                ),
                message_thread_id=node.topic_id,
            )
    elif message.voice:
        if node.reply_to_message:
            await node.reply_to_message.reply_voice(
                file_name,
                caption=caption,
                message_thread_id=node.topic_id,
            )
        else:
            await upload_user.send_voice(
                upload_telegram_chat_id,
                file_name,
                caption=caption,
                progress=update_upload_stat,
                progress_args=(
                    message.id,
                    ui_file_name,
                    time.time(),
                    node,
                    upload_user,
                ),
                message_thread_id=node.topic_id,
            )
    elif message.video_note:
        if node.reply_to_message:
            await node.reply_to_message.reply_video_note(
                file_name,
                caption=caption,
                message_thread_id=node.topic_id,
            )
        else:
            await upload_user.send_video_note(
                upload_telegram_chat_id,
                file_name,
                caption=caption,
                progress=update_upload_stat,
                progress_args=(
                    message.id,
                    ui_file_name,
                    time.time(),
                    node,
                    upload_user,
                ),
                message_thread_id=node.topic_id,
            )
    elif message.text:
        if node.reply_to_message:
            await node.reply_to_message.reply(
                message.text, message_thread_id=node.topic_id
            )
        else:
            await upload_user.send_message(
                upload_telegram_chat_id,
                message.text,
                message_thread_id=node.topic_id,
            )


async def _upload_telegram_chat_message(
    client: pyrogram.Client,
    upload_user: pyrogram.Client,
    app: Application,
    node: TaskNode,
    message: pyrogram.types.Message,
    file_name: str = None,
):
    """
    Uploads a Telegram chat message to the destination chat.

    Args:
        client (pyrogram.Client): The client used to interact with the Telegram API.
        upload_user (pyrogram.Client): The client used to upload the message.
        app (Application): The application instance.
        node (TaskNode): The task node associated with the message.
        message (pyrogram.types.Message): The Telegram chat message to be uploaded.
        file_name (str): The name of the file to be uploaded.

    Returns:
        None
    """
    await app.forward_limit_call.wait(node)

    caption = message.caption
    caption_entities = message.caption_entities

    # Convert caption and caption_entities to markdown format
    if caption and caption_entities:
        caption = pyrogram.parser.Parser.unparse(caption, caption_entities, True)

    max_caption_length = 4096 if client.me and client.me.is_premium else 1024
    # proc caption MEDIA_CAPTION_TOO_LONG
    if caption and len(caption) > max_caption_length:
        caption = caption[:max_caption_length]
        
    if message.caption:
        app.set_caption_name(node.chat_id, message.media_group_id, message.caption)
        app.set_caption_entities(
                node.chat_id, message.media_group_id, message.caption_entities
            )

    if not message.media_group_id:
        if not node.has_protected_content:
            if node.reply_to_message:
                if message.text:
                    await node.reply_to_message.reply(
                        message.text,
                        message_thread_id=node.topic_id,
                    )
                elif message.photo:
                    await node.reply_to_message.reply_photo(
                        message.photo.file_id,
                        caption=caption,
                        message_thread_id=node.topic_id,
                    )
                elif message.video:
                    await node.reply_to_message.reply_video(
                        message.video.file_id,
                        caption=caption,
                        message_thread_id=node.topic_id,
                    )
                elif message.document:
                    await node.reply_to_message.reply_document(
                        message.document.file_id,
                        caption=caption,
                        message_thread_id=node.topic_id,
                    )
                elif message.audio:
                    await node.reply_to_message.reply_audio(
                        message.audio.file_id,
                        caption=caption,
                        message_thread_id=node.topic_id,
                    )
            else:
                # For other types of media, fallback to forward_messages
                await forward_messages(
                    client,
                    node.upload_telegram_chat_id,
                    node.chat_id,
                    message.id,
                    drop_author=True,
                    topic_id=node.topic_id,
                    #caption=caption if caption != message.caption else None,
                )
        else:
            await _upload_signal_message(
                client,
                upload_user,
                app,
                node,
                node.upload_telegram_chat_id,
                message,
                file_name,
                caption,
            )
        return ForwardStatus.SuccessForward

    return await forward_multi_media(
        client, upload_user, app, node, message, caption, file_name
    )


# pylint: disable=R0912
async def forward_multi_media(
    client: pyrogram.Client,
    _: pyrogram.Client,
    app: Application,
    node: TaskNode,
    message: pyrogram.types.Message,
    caption: str = None,
    file_name: str = None,
):
    """Forward multi media by cache"""
    caption = message.caption
    caption_entities = message.caption_entities
    if not caption:
        caption = app.get_caption_name(node.chat_id, message.media_group_id)
        caption_entities = app.get_caption_entities(
            node.chat_id, message.media_group_id
        )

    # Convert caption and caption_entities to markdown format
    if caption and caption_entities:
        caption = pyrogram.parser.Parser.unparse(caption, caption_entities, True)

    max_caption_length = 4096 if client.me and client.me.is_premium else 1024
    # proc caption MEDIA_CAPTION_TOO_LONG
    if caption and len(caption) > max_caption_length:
        caption = caption[:max_caption_length]

    media_obj = get_media_obj(message, file_name, caption)
    if not node.has_protected_content:
        media = getattr(message, message.media.value)
        if not media:
            return ForwardStatus.SkipForward
        media_obj.media = media.file_id if media else ""

    async with node.media_group_ids_lock:
        if not node.media_group_ids.get(message.media_group_id):
            node.media_group_ids[message.media_group_id] = {}

        if not node.media_group_ids[message.media_group_id]:
            media_group = await get_media_group_with_retry(
                client, node.chat_id, message.id, 5
            )
            if not media_group:
                logger.error("Get Media Group Error! message id: {}", message.id)
                return ForwardStatus.FailedForward

            for it in media_group:
                node.media_group_ids[message.media_group_id][it.id] = None
                node.upload_status[message.id] = None

    if not node.media_group_ids[message.media_group_id][message.id]:
        node.upload_status[message.id] = UploadStatus.Uploading
        try:
            ui_file_name = file_name
            if file_name:
                ui_file_name = (
                    f"****{os.path.splitext(file_name)[-1]}"
                    if app.hide_file_name
                    else file_name
                )
                media_obj.thumb = (
                    await download_thumbnail(client, app.temp_save_path, message)
                    if message.video
                    else None
                )

            _media = await cache_media(
                client,
                node.upload_telegram_chat_id,  # type: ignore
                media_obj,
                progress=update_upload_stat,
                progress_args=(
                    message.id,
                    ui_file_name,
                    time.time(),
                    node,
                    client,
                ),
            )
        except Exception as e:
            logger.exception(f"{e}")
            node.upload_status[message.id] = UploadStatus.FailedUpload
        finally:
            if file_name and message.video and media_obj.thumb:
                os.remove(str(media_obj.thumb))

        if node.upload_status[message.id] == UploadStatus.FailedUpload:
            return ForwardStatus.FailedForward

        async with node.media_group_ids_lock:
            node.media_group_ids[message.media_group_id][message.id] = _media
            node.upload_status[message.id] = UploadStatus.SuccessUpload

    return await proc_cache_forward(client, node, message, bool(file_name), app)


async def proc_cache_forward(
    client: pyrogram.Client,
    node: TaskNode,
    message: pyrogram.types.Message,
    check_download_status: bool,
    app: Application
):
    """Process other cache forward"""
    multi_media: List[pyrogram.raw.types.InputSingleMedia] = []

    async with node.media_group_ids_lock:
        # Check if the message's media group is valid
        media_group = node.media_group_ids.get(message.media_group_id)
        if not media_group:
            return

        # Check if all items are in a valid state for forwarding
        for key, media_item in media_group.items():
            download_status = node.download_status.get(key, DownloadStatus.Downloading)
            upload_status = node.upload_status.get(key, UploadStatus.Uploading)

            # Skip if download is not needed or failed
            if node.skip_msg_id(key) or download_status in {DownloadStatus.SkipDownload, DownloadStatus.FailedDownload}:
                continue

            # Return if any media is still downloading or uploading
            if (
                (check_download_status and download_status == DownloadStatus.Downloading) or
                upload_status == UploadStatus.Uploading
            ):
                return ForwardStatus.CacheForward

            # Collect the media items that are valid for forwarding
            if media_item:
                if multi_media:
                    media_item.message = ""
                multi_media.append(media_item)

        # If we have multiple media, adjust the caption of the first item
        if len(multi_media) > 1 and not multi_media[0].message:
            caption = app.get_caption_name(node.chat_id, message.media_group_id)
            caption_entities = app.get_caption_entities(node.chat_id, message.media_group_id)

            multi_media[0].message, multi_media[0].entities = (await utils.parse_text_entities(client, caption, None, caption_entities)).values()

        node.media_group_ids.pop(message.media_group_id)

    forward_status = ForwardStatus.SuccessForward

    reply_to_message_id = None
    message_thread_id = node.topic_id
    business_connection_id = None
    upload_telegram_chat_id = node.upload_telegram_chat_id
    if node.reply_to_message:
        if node.reply_to_message.chat.type != pyrogram.enums.ChatType.PRIVATE:
            reply_to_message_id = node.reply_to_message.id
        message_thread_id = node.reply_to_message.message_thread_id
        business_connection_id = node.reply_to_message.business_connection_id
        upload_telegram_chat_id = node.reply_to_message.chat.id
    if not await send_media_group_v2(
        client,
        upload_telegram_chat_id,  # type: ignore
        multi_media,
        message_thread_id=message_thread_id,
        reply_to_message_id=reply_to_message_id,
        business_connection_id=business_connection_id,
    ):
        forward_status = ForwardStatus.FailedForward

    node.stat_forward(forward_status, len(multi_media))

    return ForwardStatus.CacheForward


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
    """see _report_bot_status"""
    try:
        return await _report_bot_status(client, node, immediate_reply)
    except Exception as e:
        logger.debug(f"{e}")


async def _report_bot_status(
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
                f"\n🔄 {_t('Forward')}\n"
                f"├─ 📁 {_t('Total')}: {node.total_forward_task}\n"
                f"├─ ✅ {_t('Success')}: {node.success_forward_task}\n"
                f"├─ ❌ {_t('Failed')}: {node.failed_forward_task}\n"
                f"└─ ⏩ {_t('Skipped')}: {node.skip_forward_task}\n"
            )

        upload_msg_detail_str: str = ""

        if node.upload_success_count:
            upload_msg_detail_str = (
                f"\n☁️ {_t('Upload')}\n"
                f"└─ ✅ {_t('Success')}: {node.upload_success_count}\n"
            )

        for idx, value in node.cloud_drive_upload_stat_dict.items():
            if value.transferred == value.total:
                continue

            temp_file_name = truncate_filename(os.path.basename(value.file_name), 10)
            upload_msg_detail_str += (
                f" ├─ 🆔 {_t('Message ID')}: {idx}\n"
                f" │   ├─ 📁 : {temp_file_name}\n"
                f" │   ├─ 📏 : {value.total}\n"
                f" │   ├─ ⏫ : {value.speed}\n"
                f" │   └─ 📊 : ["
                f'{create_progress_bar(int(value.percentage.split("%")[0]))}]'
                f" ({value.percentage})%\n"
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
                    f" │   ├─ ⏬ : {format_byte(value['download_speed'])}/s\n"
                    f" │   └─ 📊 : [{create_progress_bar(progress)}]"
                    f" ({progress}%)\n"
                )

            if download_result_str:
                download_result_str = (
                    f"\n📥 {_t('Download Progresses')}:\n" + download_result_str
                )

        upload_result_str = ""
        for idx, value in node.upload_stat_dict.items():
            if value.total_size == value.upload_size:
                continue

            temp_file_name = truncate_filename(os.path.basename(value.file_name), 10)
            progress = int(value.upload_size / value.total_size * 100)
            upload_result_str += (
                f" ├─ 🆔 {_t('Message ID')}: {idx}\n"
                f" │   ├─ 📁 : {temp_file_name}\n"
                f" │   ├─ 📏 : {format_byte(value.total_size)}\n"
                f" │   ├─ ⏫ : {format_byte(value.upload_speed)}/s\n"
                f" │   └─ 📊 : [{create_progress_bar(progress)}]"
                f" ({progress}%)\n"
            )

        if upload_result_str:
            upload_result_str = f"\n📤 {_t('Upload Progresses')}:\n" + upload_result_str

        new_msg_str = (
            f"`\n"
            f"🆔 task id: {node.task_id}\n"
            f"📥 {_t('Downloading')}: {format_byte(node.total_download_byte)}\n"
            f"├─ 📁 {_t('Total')}: {node.total_download_task}\n"
            f"├─ ✅ {_t('Success')}: {node.success_download_task}\n"
            f"├─ ❌ {_t('Failed')}: {node.failed_download_task}\n"
            f"└─ ⏩ {_t('Skipped')}: {node.skip_download_task}\n"
            f"{node.forward_msg_detail_str}"
            f"{upload_msg_detail_str}"
            f"{upload_result_str}"
            f"{download_result_str}\n`"
        )

        if new_msg_str != node.last_edit_msg:
            node.last_edit_msg = new_msg_str
            await client.edit_message_text(
                node.from_user_id,
                node.reply_message_id,
                new_msg_str,
                parse_mode=pyrogram.enums.ParseMode.MARKDOWN,
            )


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


async def retry(func: Callable, args: tuple = (), max_attempts=3, wait_second=15):
    """
    Asynchronously retries the provided function
    a specified number of times with a specified wait time between retries.

    :param func: The function to be retried.
    :param args: The arguments to be passed to the function.
    :param max_attempts: The maximum number of attempts to retry the function.
        Defaults to 3.
    :param wait_second: The wait time in seconds between each retry attempt.
        Defaults to 15.

    :return: The result of the function
    if it succeeds within the maximum number of attempts, otherwise None.
    """

    for _ in range(1, max_attempts + 1):
        try:
            return await func(*args)
        except pyrogram.errors.exceptions.flood_420.FloodWait as wait_err:
            logger.warning("bad call retry: FlowWait {}", wait_err.value)
            await asyncio.sleep(wait_err.value)
        except Exception as e:
            logger.exception("Error: {}", e)
            await asyncio.sleep(wait_second)

    logger.error("Failed after {} attempts", max_attempts)
    return None


async def get_media_group_with_retry(
    client: pyrogram.Client,
    chat_id: Union[int, str],
    message_id: int,
    max_attempts: int = 3,
    wait_second: int = 15,
):
    """
    get_media_group_with_retry
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await client.get_media_group(chat_id, message_id)
        except Exception as e:
            if attempt == max_attempts:
                logger.error("Failed Get Media Group[{}]", message_id)
                return types.List()

            logger.exception("Get Message[{}]: Error {}", message_id, e)
            await asyncio.sleep(wait_second)
    return types.List()


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

    meta_data.message_thread_id = getattr(message, "message_thread_id", 1)
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


async def parse_link(client: pyrogram.Client, link_str: str):
    """Parse link"""
    link = extract_info_from_link(link_str)
    if link.comment_id:
        chat = await client.get_chat(link.group_id)
        if chat:
            return chat.linked_chat.id, link.comment_id, link.topic_id

    return link.group_id, link.post_id, link.topic_id


async def update_cloud_upload_stat(
    transferred: str,
    total: str,
    percentage: str,
    speed: str,
    eta: str,
    node: TaskNode,
    message_id: int,
    file_name: str,
):
    """
    Update the cloud upload statistics with the given information.

    Args:
        transferred (str): The amount of data transferred.
        total (str): The total size of the file.
        percentage (str): The percentage of the file uploaded.
        speed (str): The upload speed.
        eta (str): The estimated time of arrival for the upload to complete.
        node (TaskNode): The task node associated with the upload.
        message_id (int): The ID of the message.
        file_name (str): The name of the file being uploaded.

    Returns:
        None
    """
    node.cloud_drive_upload_stat_dict[message_id] = CloudDriveUploadStat(
        file_name=file_name,
        transferred=transferred,
        total=total,
        percentage=percentage,
        speed=speed,
        eta=eta,
    )


async def update_upload_stat(
    upload_size: int,
    total_size: int,
    message_id: int,
    file_name: str,
    start_time: float,
    node: TaskNode,
    client: pyrogram.Client,
):
    """update_upload_status"""
    cur_time = time.time()

    if node.is_stop_transmission:
        client.stop_transmission()

    # TODO(tyh): web control upload stop

    if node.upload_stat_dict.get(message_id):
        upload_stat = node.upload_stat_dict[message_id]

        if cur_time - upload_stat.last_stat_time >= 1.0:
            upload_stat.upload_speed = max(
                int(
                    (upload_size - upload_stat.upload_size)
                    / (cur_time - upload_stat.last_stat_time)
                ),
                0,
            )
            upload_stat.last_stat_time = cur_time
            upload_stat.upload_size = upload_size

        node.upload_stat_dict[message_id] = upload_stat
    else:
        duration = cur_time - start_time
        upload_stat = UploadProgressStat(
            file_name=file_name,
            total_size=total_size,
            upload_size=upload_size,
            start_time=start_time,
            last_stat_time=cur_time,
            upload_speed=upload_size / (duration if duration > 0 else 1),
        )
        node.upload_stat_dict[message_id] = upload_stat


# pylint: enable=W0201
class HookSession(pyrogram.session.Session):
    """Hook Session"""

    def start_timeout(self: pyrogram.session.Session, start_timeout: int):
        """
        Set the start timeout for the session.

        Args:
            start_timeout (int): The start timeout value in seconds.

        Returns:
            None
        """
        self.START_TIMEOUT = start_timeout


# pylint: disable=all
class HookClient(pyrogram.Client):
    """Hook Client"""

    # pylint: disable=R0901
    START_TIME_OUT = 60

    def __init__(self, name: str, **kwargs):
        if "start_timeout" in kwargs:
            value = kwargs.get("start_timeout")
            if value:
                self.START_TIME_OUT = value
            kwargs.pop("start_timeout")

        super().__init__(name, **kwargs)

    async def connect(
        self,
    ) -> bool:
        """
        Connects the client to the server.

        Returns:
            bool: True if the client successfully
                connects to the server, False otherwise.

        Raises:
            ConnectionError: If the client is already connected.

        """
        if self.is_connected:  # type: ignore
            raise ConnectionError("Client is already connected")

        await self.load_session()

        self.session = HookSession(
            self,
            await self.storage.dc_id(),
            await self.storage.auth_key(),
            await self.storage.test_mode(),
        )
        self.session.start_timeout(self.START_TIME_OUT)

        await self.session.start()

        self.is_connected = True

        return bool(await self.storage.user_id())

    async def start(self):
        """
        Starts the client by performing necessary initialization steps.

        Returns:
            The initialized client instance.
        """
        is_authorized = await self.connect()

        try:
            if not is_authorized:
                await self.authorize()

            if not await self.storage.is_bot() and self.takeout:
                self.takeout_id = (
                    await self.invoke(
                        pyrogram.raw.functions.account.InitTakeoutSession()
                    )
                ).id
                logger.warning(f"Takeout session {self.takeout_id} initiated")

            await self.invoke(pyrogram.raw.functions.updates.GetState())
        except (Exception, KeyboardInterrupt):
            await self.disconnect()
            raise
        else:
            self.me = await self.get_me()
            await self.initialize()

            return self


# pylint: disable=R0914,R0913
async def forward_messages(
    client: pyrogram.Client,
    chat_id: Union[int, str, None],
    from_chat_id: Union[int, str],
    message_ids: Union[int, Iterable[int]],
    disable_notification: bool = None,
    schedule_date: datetime = None,
    protect_content: bool = None,
    drop_author: bool = None,
    topic_id: int = None,
    caption: str = None,
    caption_entities: List[pyrogram.types.MessageEntity] = None,
) -> Union["types.Message", List["types.Message"]]:
    """Forward messages of any kind."""

    is_iterable = not isinstance(message_ids, int)
    message_ids = list(message_ids) if is_iterable else [message_ids]  # type: ignore

    r = await client.invoke(
        pyrogram.raw.functions.messages.ForwardMessages(
            to_peer=await client.resolve_peer(chat_id),
            from_peer=await client.resolve_peer(from_chat_id),
            id=message_ids,
            silent=disable_notification or None,
            random_id=[client.rnd_id() for _ in message_ids],
            schedule_date=pyrogram.utils.datetime_to_timestamp(schedule_date),
            noforwards=protect_content,
            drop_author=drop_author,
            top_msg_id=topic_id,
        )
    )

    forwarded_messages = []

    users = {i.id: i for i in r.users}
    chats = {i.id: i for i in r.chats}

    for i in r.updates:
        if isinstance(
            i,
            (
                pyrogram.raw.types.UpdateNewMessage,
                pyrogram.raw.types.UpdateNewChannelMessage,
                pyrogram.raw.types.UpdateNewScheduledMessage,
            ),
        ):
            forwarded_messages.append(
                # pylint: disable=W0212
                await types.Message._parse(client, i.message, users, chats)
            )

    if caption and not is_iterable and forwarded_messages:
        await client.edit_message_caption(
            chat_id, forwarded_messages[0].id, caption=caption
        )

    return types.List(forwarded_messages) if is_iterable else forwarded_messages[0]
