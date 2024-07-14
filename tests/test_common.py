import datetime
import platform

from pyrogram.file_id import PHOTO_TYPES, FileType


class Chat:
    def __init__(self, chat_id, chat_title):
        self.id = chat_id
        self.title = chat_title


class Date:
    def __init__(self, date):
        self.date = date

    def strftime(self, str) -> str:
        return ""


class MockMessage:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.media = kwargs.get("media")
        self.audio = kwargs.get("audio", None)
        self.document = kwargs.get("document", None)
        self.photo = kwargs.get("photo", None)
        self.video = kwargs.get("video", None)
        self.voice = kwargs.get("voice", None)
        self.video_note = kwargs.get("video_note", None)
        self.media_group_id = kwargs.get("media_group_id", None)
        self.caption = kwargs.get("caption", None)
        self.text = kwargs.get("text", None)
        self.empty = kwargs.get("empty", False)
        self.from_user = kwargs.get("from_user", None)
        self.reply_to_message_id = kwargs.get("reply_to_message_id", None)

        if kwargs.get("dis_chat") == None:
            self.chat = Chat(
                kwargs.get("chat_id", None), kwargs.get("chat_title", None)
            )
        else:
            self.chat = kwargs.get("chat", None)
        self.date: datetime = None
        if kwargs.get("date") != None:
            self.date = kwargs["date"]


class MockUser:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 0)
        self.username = kwargs.get("username", "")


class MockAudio:
    def __init__(self, **kwargs):
        self.file_name = kwargs["file_name"]
        self.mime_type = kwargs["mime_type"]
        self.file_id = "AUDIO"
        if kwargs.get("file_size"):
            self.file_size = kwargs["file_size"]
        else:
            self.file_size = 1024


class MockDocument:
    def __init__(self, **kwargs):
        self.file_name = kwargs["file_name"]
        self.mime_type = kwargs["mime_type"]
        self.file_id = "DOCUMENT"
        if kwargs.get("file_size"):
            self.file_size = kwargs["file_size"]
        else:
            self.file_size = 1024


class MockPhoto:
    def __init__(self, **kwargs):
        self.date = kwargs["date"]
        self.file_unique_id = kwargs["file_unique_id"]
        self.file_id = "PHOTO"
        if kwargs.get("file_size"):
            self.file_size = kwargs["file_size"]
        else:
            self.file_size = 1024


class MockVoice:
    def __init__(self, **kwargs):
        self.mime_type = kwargs["mime_type"]
        self.date = kwargs["date"]
        self.file_id = "VOICE"
        if kwargs.get("file_size"):
            self.file_size = kwargs["file_size"]
        else:
            self.file_size = 1024


class MockVideo:
    def __init__(self, **kwargs):
        self.file_name = kwargs.get("file_name")
        self.mime_type = kwargs["mime_type"]
        self.file_id = "VIDEO"
        if kwargs.get("file_size"):
            self.file_size = kwargs["file_size"]
        else:
            self.file_size = 1024

        if kwargs.get("width"):
            self.width = kwargs["width"]
        else:
            self.width = 1920

        if kwargs.get("height"):
            self.height = kwargs["height"]
        else:
            self.height = 1080

        if kwargs.get("duration"):
            self.duration = kwargs["duration"]
        else:
            self.duration = 1024


class MockVideoNote:
    def __init__(self, **kwargs):
        self.mime_type = kwargs["mime_type"]
        self.file_id = "VIDEO_NOTE"
        self.date = kwargs["date"]


def platform_generic_path(_path: str) -> str:
    platform_specific_path: str = _path
    if platform.system() == "Windows":
        platform_specific_path = platform_specific_path.replace("/", "\\")
    return platform_specific_path


def get_file_type(file_id: str):
    if file_id == "THUMBNAIL":
        return FileType.THUMBNAIL
    elif file_id == "CHAT_PHOTO":
        return FileType.CHAT_PHOTO
    elif file_id == "PHOTO":
        return FileType.PHOTO
    elif file_id == "VOICE":
        return FileType.VOICE
    elif file_id == "VIDEO":
        return FileType.VIDEO
    elif file_id == "DOCUMENT":
        return FileType.DOCUMENT
    elif file_id == "ENCRYPTED":
        return FileType.ENCRYPTED
    elif file_id == "TEMP":
        return FileType.TEMP
    elif file_id == "STICKER":
        return FileType.STICKER
    elif file_id == "AUDIO":
        return FileType.AUDIO
    elif file_id == "ANIMATION":
        return FileType.ANIMATION
    elif file_id == "ENCRYPTED_THUMBNAIL":
        return FileType.ENCRYPTED_THUMBNAIL
    elif file_id == "WALLPAPER":
        return FileType.WALLPAPER
    elif file_id == "VIDEO_NOTE":
        return FileType.VIDEO_NOTE
    elif file_id == "SECURE_RAW":
        return FileType.SECURE_RAW
    elif file_id == "SECURE":
        return FileType.SECURE
    elif file_id == "BACKGROUND":
        return FileType.BACKGROUND
    elif file_id == "DOCUMENT_AS_FILE":
        return FileType.DOCUMENT_AS_FILE

    raise ValueError("error file id!")


def get_extension(file_id: str, mime_type: str, dot: bool = True):
    file_type = get_file_type(file_id=file_id)
    guessed_extension = ""

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
