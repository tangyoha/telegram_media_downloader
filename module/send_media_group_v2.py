"""send media group"""
import logging
import os
import re
from datetime import datetime
from typing import Callable, List, Optional, Union

import pyrogram
from pyrogram import raw, types, utils
from pyrogram.file_id import FileType

log = logging.getLogger(__name__)

# pylint: disable = R0915, R0902, R0912
async def cache_media(
    client: pyrogram.Client,
    chat_id: Union[int, str],
    media_obj: Union[
        "types.InputMediaPhoto",
        "types.InputMediaVideo",
        "types.InputMediaAudio",
        "types.InputMediaDocument",
    ],
    progress: Callable = None,
    progress_args: tuple = (),
) -> raw.base.InputSingleMedia:
    """
    Caches a media.

    :param client: The pyrogram.Client instance.
    :param chat_id: The ID of the chat.
    :param media: The media to be cached.
    :return: The cached media.
    """
    if isinstance(media_obj, types.InputMediaPhoto):
        if isinstance(media_obj.media, str):
            if os.path.isfile(media_obj.media):
                media = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await client.resolve_peer(chat_id),
                        media=raw.types.InputMediaUploadedPhoto(
                            file=await client.save_file(
                                media_obj.media,
                                progress=progress,
                                progress_args=progress_args,
                            )
                        ),
                    )
                )

                media = raw.types.InputMediaPhoto(
                    id=raw.types.InputPhoto(
                        id=media.photo.id,
                        access_hash=media.photo.access_hash,
                        file_reference=media.photo.file_reference,
                    )
                )
            elif re.match("^https?://", media_obj.media):
                media = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await client.resolve_peer(chat_id),
                        media=raw.types.InputMediaPhotoExternal(url=media_obj.media),
                    )
                )

                media = raw.types.InputMediaPhoto(
                    id=raw.types.InputPhoto(
                        id=media.photo.id,
                        access_hash=media.photo.access_hash,
                        file_reference=media.photo.file_reference,
                    )
                )
            else:
                media = utils.get_input_media_from_file_id(
                    media_obj.media, FileType.PHOTO
                )
        else:
            media = await client.invoke(
                raw.functions.messages.UploadMedia(
                    peer=await client.resolve_peer(chat_id),
                    media=raw.types.InputMediaUploadedPhoto(
                        file=await client.save_file(
                            media_obj.media,
                            progress=progress,
                            progress_args=progress_args,
                        )
                    ),
                )
            )

            media = raw.types.InputMediaPhoto(
                id=raw.types.InputPhoto(
                    id=media.photo.id,
                    access_hash=media.photo.access_hash,
                    file_reference=media.photo.file_reference,
                )
            )
    elif isinstance(media_obj, types.InputMediaVideo):
        if isinstance(media_obj.media, str):
            if os.path.isfile(media_obj.media):
                media = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await client.resolve_peer(chat_id),
                        media=raw.types.InputMediaUploadedDocument(
                            file=await client.save_file(
                                media_obj.media,
                                progress=progress,
                                progress_args=progress_args,
                            ),
                            thumb=await client.save_file(media_obj.thumb),
                            mime_type=client.guess_mime_type(media_obj.media)
                            or "video/mp4",
                            nosound_video=True,
                            attributes=[
                                raw.types.DocumentAttributeVideo(
                                    supports_streaming=media_obj.supports_streaming
                                    or None,
                                    duration=media_obj.duration,
                                    w=media_obj.width,
                                    h=media_obj.height,
                                ),
                                raw.types.DocumentAttributeFilename(
                                    file_name=os.path.basename(media_obj.media)
                                ),
                            ],
                        ),
                    )
                )

                media = raw.types.InputMediaDocument(
                    id=raw.types.InputDocument(
                        id=media.document.id,
                        access_hash=media.document.access_hash,
                        file_reference=media.document.file_reference,
                    )
                )
            elif re.match("^https?://", media_obj.media):
                media = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await client.resolve_peer(chat_id),
                        media=raw.types.InputMediaDocumentExternal(url=media_obj.media),
                    )
                )

                media = raw.types.InputMediaDocument(
                    id=raw.types.InputDocument(
                        id=media.document.id,
                        access_hash=media.document.access_hash,
                        file_reference=media.document.file_reference,
                    )
                )
            else:
                media = utils.get_input_media_from_file_id(
                    media_obj.media, FileType.VIDEO
                )
        else:
            media = await client.invoke(
                raw.functions.messages.UploadMedia(
                    peer=await client.resolve_peer(chat_id),
                    media=raw.types.InputMediaUploadedDocument(
                        file=await client.save_file(
                            media_obj.media,
                            progress=progress,
                            progress_args=progress_args,
                        ),
                        thumb=await client.save_file(media_obj.thumb),
                        mime_type=client.guess_mime_type(
                            getattr(media_obj.media, "name", "video.mp4")
                        )
                        or "video/mp4",
                        nosound_video=True,
                        attributes=[
                            raw.types.DocumentAttributeVideo(
                                supports_streaming=media_obj.supports_streaming or None,
                                duration=media_obj.duration,
                                w=media_obj.width,
                                h=media_obj.height,
                            ),
                            raw.types.DocumentAttributeFilename(
                                file_name=getattr(media_obj.media, "name", "video.mp4")
                            ),
                        ],
                    ),
                )
            )

            media = raw.types.InputMediaDocument(
                id=raw.types.InputDocument(
                    id=media.document.id,
                    access_hash=media.document.access_hash,
                    file_reference=media.document.file_reference,
                )
            )
    elif isinstance(media_obj, types.InputMediaAudio):
        if isinstance(media_obj.media, str):
            if os.path.isfile(media_obj.media):
                media = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await client.resolve_peer(chat_id),
                        media=raw.types.InputMediaUploadedDocument(
                            mime_type=client.guess_mime_type(media_obj.media)
                            or "audio/mpeg",
                            file=await client.save_file(
                                media_obj.media,
                                progress=progress,
                                progress_args=progress_args,
                            ),
                            thumb=await client.save_file(media_obj.thumb),
                            attributes=[
                                raw.types.DocumentAttributeAudio(
                                    duration=media_obj.duration,
                                    performer=media_obj.performer,
                                    title=media_obj.title,
                                ),
                                raw.types.DocumentAttributeFilename(
                                    file_name=os.path.basename(media_obj.media)
                                ),
                            ],
                        ),
                    )
                )

                media = raw.types.InputMediaDocument(
                    id=raw.types.InputDocument(
                        id=media.document.id,
                        access_hash=media.document.access_hash,
                        file_reference=media.document.file_reference,
                    )
                )
            elif re.match("^https?://", media_obj.media):
                media = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await client.resolve_peer(chat_id),
                        media=raw.types.InputMediaDocumentExternal(url=media_obj.media),
                    )
                )

                media = raw.types.InputMediaDocument(
                    id=raw.types.InputDocument(
                        id=media.document.id,
                        access_hash=media.document.access_hash,
                        file_reference=media.document.file_reference,
                    )
                )
            else:
                media = utils.get_input_media_from_file_id(
                    media_obj.media, FileType.AUDIO
                )
        else:
            media = await client.invoke(
                raw.functions.messages.UploadMedia(
                    peer=await client.resolve_peer(chat_id),
                    media=raw.types.InputMediaUploadedDocument(
                        mime_type=client.guess_mime_type(
                            getattr(media_obj.media, "name", "audio.mp3")
                        )
                        or "audio/mpeg",
                        file=await client.save_file(
                            media_obj.media,
                            progress=progress,
                            progress_args=progress_args,
                        ),
                        thumb=await client.save_file(media_obj.thumb),
                        attributes=[
                            raw.types.DocumentAttributeAudio(
                                duration=media_obj.duration,
                                performer=media_obj.performer,
                                title=media_obj.title,
                            ),
                            raw.types.DocumentAttributeFilename(
                                file_name=getattr(media_obj.media, "name", "audio.mp3")
                            ),
                        ],
                    ),
                )
            )

            media = raw.types.InputMediaDocument(
                id=raw.types.InputDocument(
                    id=media.document.id,
                    access_hash=media.document.access_hash,
                    file_reference=media.document.file_reference,
                )
            )
    elif isinstance(media_obj, types.InputMediaDocument):
        if isinstance(media_obj.media, str):
            if os.path.isfile(media_obj.media):
                media = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await client.resolve_peer(chat_id),
                        media=raw.types.InputMediaUploadedDocument(
                            mime_type=client.guess_mime_type(media_obj.media)
                            or "application/zip",
                            file=await client.save_file(
                                media_obj.media,
                                progress=progress,
                                progress_args=progress_args,
                            ),
                            thumb=await client.save_file(media_obj.thumb),
                            attributes=[
                                raw.types.DocumentAttributeFilename(
                                    file_name=os.path.basename(media_obj.media)
                                )
                            ],
                        ),
                    )
                )

                media = raw.types.InputMediaDocument(
                    id=raw.types.InputDocument(
                        id=media.document.id,
                        access_hash=media.document.access_hash,
                        file_reference=media.document.file_reference,
                    )
                )
            elif re.match("^https?://", media_obj.media):
                media = await client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await client.resolve_peer(chat_id),
                        media=raw.types.InputMediaDocumentExternal(url=media_obj.media),
                    )
                )

                media = raw.types.InputMediaDocument(
                    id=raw.types.InputDocument(
                        id=media.document.id,
                        access_hash=media.document.access_hash,
                        file_reference=media.document.file_reference,
                    )
                )
            else:
                media = utils.get_input_media_from_file_id(
                    media_obj.media, FileType.DOCUMENT
                )
        else:
            media = await client.invoke(
                raw.functions.messages.UploadMedia(
                    peer=await client.resolve_peer(chat_id),
                    media=raw.types.InputMediaUploadedDocument(
                        mime_type=client.guess_mime_type(
                            getattr(media_obj.media, "name", "file.zip")
                        )
                        or "application/zip",
                        file=await client.save_file(
                            media_obj.media,
                            progress=progress,
                            progress_args=progress_args,
                        ),
                        thumb=await client.save_file(media_obj.thumb),
                        attributes=[
                            raw.types.DocumentAttributeFilename(
                                file_name=getattr(media_obj.media, "name", "file.zip")
                            )
                        ],
                    ),
                )
            )

            media = raw.types.InputMediaDocument(
                id=raw.types.InputDocument(
                    id=media.document.id,
                    access_hash=media.document.access_hash,
                    file_reference=media.document.file_reference,
                )
            )
    else:
        raise ValueError(
            f"{media_obj.__class__.__name__}"
            " is not a supported type for send_media_group"
        )

    return raw.types.InputSingleMedia(
        media=media,
        random_id=client.rnd_id(),
        **await client.parser.parse(
            media_obj.caption
            if media_obj.caption and media_obj.caption != "None"
            else ""
        ),
    )


# pylint: disable = R0913
async def send_media_group_v2(
    client: pyrogram.Client,
    chat_id: Union[int, str],
    multi_media: List[raw.types.InputSingleMedia],
    disable_notification: bool = None,
    schedule_date: datetime = None,
    quote_text: str = None,
    parse_mode: Optional["pyrogram.enums.ParseMode"] = None,
    message_thread_id: int = None,
    reply_to_message_id: int = None,
    reply_to_chat_id: Union[int, str] = None,
    reply_to_story_id: int = None,
    quote_entities: List["types.MessageEntity"] = None,
    quote_offset: int = None,
    show_above_text: bool = None,
):
    """
    see pyrogram
    """
    quote_text, quote_entities = (
        await utils.parse_text_entities(client, quote_text, parse_mode, quote_entities)
    ).values()

    r = await client.invoke(
        raw.functions.messages.SendMultiMedia(
            peer=await client.resolve_peer(chat_id),
            multi_media=multi_media,
            silent=disable_notification or None,
            reply_to=utils.get_reply_to(
                reply_to_message_id=reply_to_message_id,
                message_thread_id=message_thread_id,
                reply_to_peer=await client.resolve_peer(reply_to_chat_id)
                if reply_to_chat_id
                else None,
                reply_to_story_id=reply_to_story_id,
                quote_text=quote_text,
                quote_entities=quote_entities,
                quote_offset=quote_offset,
            ),
            schedule_date=utils.datetime_to_timestamp(schedule_date),
            invert_media=show_above_text,
        ),
        sleep_threshold=60,
    )

    return await utils.parse_messages(
        client,
        raw.types.messages.Messages(
            messages=[
                m.message
                for m in filter(
                    lambda u: isinstance(
                        u,
                        (
                            raw.types.UpdateNewMessage,
                            raw.types.UpdateNewChannelMessage,
                            raw.types.UpdateNewScheduledMessage,
                        ),
                    ),
                    r.updates,
                )
            ],
            users=r.users,
            chats=r.chats,
        ),
    )
