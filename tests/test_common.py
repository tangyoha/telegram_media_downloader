import datetime


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

        if kwargs.get("dis_chat") == None:
            self.chat = Chat(
                kwargs.get("chat_id", None), kwargs.get("chat_title", None)
            )
        else:
            self.chat = None
        self.date: datetime = None
        if kwargs.get("date") != None:
            self.date = kwargs["date"]


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
