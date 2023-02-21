"""Pyrogram ext"""

import struct
from io import BytesIO, StringIO
from mimetypes import MimeTypes
from typing import Optional

from pyrogram.file_id import (
    FILE_REFERENCE_FLAG,
    PHOTO_TYPES,
    WEB_LOCATION_FLAG,
    FileType,
    b64_decode,
    rle_decode,
)
from pyrogram.mime_types import mime_types

_mimetypes = MimeTypes()
_mimetypes.readfp(StringIO(mime_types))


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
