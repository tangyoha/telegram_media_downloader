"""Unittest module for media downloader."""
import asyncio
import os
import platform
import unittest
from datetime import datetime
from typing import List

import mock
import pyrogram
from pyrogram.file_id import PHOTO_TYPES, FileType

from media_downloader import (
    _can_download,
    _check_config,
    _get_media_meta,
    _is_exist,
    app,
    download_media,
    download_task,
    download_all_chat,
    worker,
    main,
)
from module.app import DownloadStatus
from module.cloud_drive import CloudDriveConfig

from .test_common import (
    Chat,
    Date,
    MockAudio,
    MockDocument,
    MockMessage,
    MockPhoto,
    MockVideo,
    MockVideoNote,
    MockVoice,
)

MOCK_DIR: str = "/root/project"
if platform.system() == "Windows":
    MOCK_DIR = "\\root\\project"
MOCK_CONF = {
    "api_id": 123,
    "api_hash": "hasw5Tgawsuj67",
    "chat": [{"chat_id": 8654123, "last_read_message_id": 0,
             "ids_to_retry": [1, 2]}],
    "media_types": ["audio", "voice"],
    "file_formats": {"audio": ["all"], "voice": ["all"]},
    "save_path": MOCK_DIR,
    "file_name_prefix": ["message_id", "caption", "file_name"],
}


def os_remove(_: str):
    pass


def is_exist(file: str):
    if os.path.basename(file).find("311 - sucess_exist_down.mp4") != -1:
        return True
    elif os.path.basename(file).find("422 - exception.mov") != -1:
        raise Exception
    return False


def os_get_file_size(file: str) -> int:
    if os.path.basename(file).find("311 - failed_down.mp4") != -1:
        return 0
    elif os.path.basename(file).find("311 - sucess_down.mp4") != -1:
        return 1024
    return 0

def new_set_download_id(chat_id: str | int, message_id: int, download_status: DownloadStatus):
    if download_status is DownloadStatus.SuccessDownload:
        app.total_download_task += 1
    if chat_id not in app.chat_download_config:
        return
    app.chat_download_config[chat_id].last_read_message_id = max(
        app.chat_download_config[chat_id].last_read_message_id, message_id)
    if download_status is not DownloadStatus.FailedDownload:
        app.chat_download_config[chat_id].downloaded_ids.append(
            message_id)
    else:
        app.chat_download_config[chat_id].failed_ids.append(message_id)
    app.is_running = False

def rest_app(conf: dict):
    app.total_download_task = 0
    app.is_running = True
    app.downloaded_ids: list = []
    # app.already_download_ids_set = set()
    app.failed_ids: list = []
    app.disable_syslog: list = []
    app.save_path = os.path.abspath(".")
    app.ids_to_retry: list = []
    app.api_id: str = ""
    app.api_hash: str = ""
    app.chat_id: str = ""
    app.media_types: List[str] = []
    app.file_formats: dict = {}
    app.proxy: dict = {}
    app.last_read_message_id = 0
    app.restart_program = False
    app.config: dict = {}
    app.app_data: dict = {}
    app.file_path_prefix: List[str] = ["chat_title", "media_datetime"]
    app.file_name_prefix: List[str] = ["message_id", "file_name"]
    app.file_name_prefix_split: str = " - "
    app.log_file_path = os.path.join(os.path.abspath("."), "log")
    app.cloud_drive_config = CloudDriveConfig()
    app.hide_file_name = False
    app.caption_name_dict: dict = {}
    app.max_concurrent_transmissions: int = 1
    app.web_host: str = "localhost"
    app.web_port: int = 5000
    app.download_filter_dict: dict = {}
    app.config_file = "config_test.yaml"
    app.app_data_file = "data_test.yaml"
    app.config = conf
    app.assign_config(conf)
    app.assign_app_data(conf)


def platform_generic_path(_path: str) -> str:
    platform_specific_path: str = _path
    if platform.system() == "Windows":
        platform_specific_path = platform_specific_path.replace("/", "\\")
    return platform_specific_path


def mock_manage_duplicate_file(file_path: str) -> str:
    return file_path


def raise_keyboard_interrupt():
    raise KeyboardInterrupt


def raise_exception():
    raise Exception


def load_config():
    raise ValueError("error load config")


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


def get_extension(file_id: str, mime_type: str):
    file_type = get_file_type(file_id=file_id)
    guessed_extension = ""

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


class MyQueue:
    async def get():
        return (MockMessage(
                id=7,
                media=True,
                chat_id=123456,
                chat_title="123456",
                date=datetime.now(),
                video=MockVideo(
                    file_name="sample_video.mov",
                    mime_type="video/mov",
                ),
                ), 8654123)


class MockEventLoop:
    def __init__(self):
        pass

    def run_until_complete(self, *args, **kwargs):
        return {"api_id": 1, "api_hash": "asdf", "ids_to_retry": [1, 2, 3]}


class MockAsync:
    def __init__(self):
        pass

    def get_event_loop(self):
        return MockEventLoop()


async def async_get_media_meta(chat_id, message, message_media, _type):
    result = await _get_media_meta(chat_id, message, message_media, _type)
    return result


async def async_download_media(client, message, media_types, file_formats, chat_id=-123):
    result = await download_media(client, message, media_types, file_formats, chat_id)
    return result


async def mock_process_message(*args, **kwargs):
    return 5


class MockClient:
    def __init__(self, *args, **kwargs):
        pass

    def __aiter__(self):
        return self

    async def start(self):
        pass

    async def stop(self):
        pass

    async def get_chat_history(self, *args, **kwargs):
        items = [
            MockMessage(
                id=1213,
                media=True,
                voice=MockVoice(
                    mime_type="audio/ogg",
                    date=datetime(2019, 7, 25, 14, 53, 50),
                ),
            ),
            MockMessage(
                id=1214,
                media=False,
                text="test message 1",
            ),
            MockMessage(
                id=1215,
                media=False,
                text="test message 2",
            ),
            MockMessage(
                id=1216,
                media=False,
                text="test message 3",
            ),
        ]
        for item in items:
            yield item

    async def get_messages(self, *args, **kwargs):
        if kwargs["message_ids"] == 7:
            return MockMessage(
                id=7,
                media=True,
                chat_id=123456,
                chat_title="123456",
                date=datetime.now(),
                video=MockVideo(
                    file_name="sample_video.mov",
                    mime_type="video/mov",
                ),
            )
        elif kwargs["message_ids"] == 8:
            return MockMessage(
                id=8,
                media=True,
                chat_id=234567,
                chat_title="234567",
                date=datetime.now(),
                video=MockVideo(
                    file_name="sample_video.mov",
                    mime_type="video/mov",
                ),
            )
        elif kwargs["message_ids"] == [1, 2]:
            return [
                MockMessage(
                    id=1,
                    media=True,
                    chat_id=234568,
                    chat_title="234568",
                    date=datetime.now(),
                    video=MockVideo(
                        file_name="sample_video.mov",
                        mime_type="video/mov",
                    ),
                ),
                MockMessage(
                    id=2,
                    media=True,
                    chat_id=234568,
                    chat_title="234568",
                    date=datetime.now(),
                    video=MockVideo(
                        file_name="sample_video2.mov",
                        mime_type="video/mov",
                    ),
                ),
            ]
        return []

    async def download_media(self, *args, **kwargs):
        mock_message = args[0]
        if mock_message.id in [7, 8]:
            raise pyrogram.errors.exceptions.bad_request_400.BadRequest
        elif mock_message.id == 9:
            raise pyrogram.errors.exceptions.unauthorized_401.Unauthorized
        elif mock_message.id == 11:
            raise TypeError
        elif mock_message.id == 420:
            raise pyrogram.errors.exceptions.flood_420.FloodWait(value=420)
        elif mock_message.id == 421:
            raise Exception
        return kwargs["file_name"]


class MediaDownloaderTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.get_event_loop()
        rest_app(MOCK_CONF)

    @mock.patch("media_downloader.get_extension", new=get_extension)
    # @mock.patch("media_downloader.app.save_path", new=MOCK_DIR)
    def test_get_media_meta(self):
        rest_app(MOCK_CONF)
        app.save_path = MOCK_DIR
        # Test Voice notes
        message = MockMessage(
            id=1,
            media=True,
            chat_title="test1",
            date=datetime(2019, 7, 25, 14, 53, 50),
            voice=MockVoice(
                mime_type="audio/ogg",
                date=datetime(2019, 7, 25, 14, 53, 50),
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.voice, "voice")
        )

        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test1/2019_07/1 - voice_2019-07-25T14:53:50.ogg"
                ),
                "ogg",
            ),
            result,
        )

        # Test photos
        message = MockMessage(
            id=2,
            media=True,
            date=datetime(2019, 8, 5, 14, 35, 12),
            chat_title="test2",
            photo=MockPhoto(
                date=datetime(2019, 8, 5, 14, 35, 12), file_unique_id="ADAVKJYIFV"
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.photo, "photo")
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test2/2019_08/2 - ADAVKJYIFV.jpg"),
                None,
            ),
            result,
        )

        message = MockMessage(
            id=2,
            media=True,
            date=datetime(2019, 8, 5, 14, 35, 12),
            chat_title="test2",
            media_group_id="AAA213213",
            caption="#home #book",
            photo=MockPhoto(
                date=datetime(2019, 8, 5, 14, 35, 12), file_unique_id="ADAVKJYIFV"
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.photo, "photo")
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test2/2019_08/2 - #home #book - ADAVKJYIFV.jpg"
                ),
                None,
            ),
            result,
        )

        # Test Documents
        message = MockMessage(
            id=3,
            media=True,
            chat_title="test2",
            document=MockDocument(
                file_name="sample_document.pdf",
                mime_type="application/pdf",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.document, "document")
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test2/0/3 - sample_document.pdf"),
                "pdf",
            ),
            result,
        )

        before_file_name_prefix_split = app.file_name_prefix_split
        app.file_name_prefix_split = "-"

        message = MockMessage(
            id=3,
            media=True,
            chat_title="test2",
            media_group_id="BBB213213",
            caption="#work",
            document=MockDocument(
                file_name="sample_document.pdf",
                mime_type="application/pdf",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.document, "document")
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test2/0/3-#work-sample_document.pdf"
                ),
                "pdf",
            ),
            result,
        )

        app.file_name_prefix_split = before_file_name_prefix_split
        # Test audio
        message = MockMessage(
            id=4,
            media=True,
            date=datetime(2021, 8, 5, 14, 35, 12),
            chat_title="test2",
            audio=MockAudio(
                file_name="sample_audio.mp3",
                mime_type="audio/mp3",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.audio, "audio")
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test2/2021_08/4 - sample_audio.mp3"
                ),
                "mp3",
            ),
            result,
        )

        # Test Video 1
        message = MockMessage(
            id=5,
            media=True,
            date=datetime(2022, 8, 5, 14, 35, 12),
            chat_title="test2",
            video=MockVideo(
                mime_type="video/mp4",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.video, "video")
        )
        self.assertEqual(
            (
                platform_generic_path("/root/project/test2/2022_08/5.mp4"),
                "mp4",
            ),
            result,
        )

        # Test Video 2
        message = MockMessage(
            id=5,
            media=True,
            date=datetime(2022, 8, 5, 14, 35, 12),
            chat_title="test2",
            video=MockVideo(
                file_name="test.mp4",
                mime_type="video/mp4",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.video, "video")
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test2/2022_08/5 - test.mp4"),
                "mp4",
            ),
            result,
        )

        # Test Video 3: not exist chat_title
        message = MockMessage(
            id=5,
            media=True,
            dis_chat=True,
            date=datetime(2022, 8, 5, 14, 35, 12),
            video=MockVideo(
                file_name="test.mp4",
                mime_type="video/mp4",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message, message.video, "video")
        )

        print(app.chat_id)
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/-123/2022_08/5 - test.mp4"),
                "mp4",
            ),
            result,
        )

        # Test VideoNote
        message = MockMessage(
            id=6,
            media=True,
            date=datetime(2019, 7, 25, 14, 53, 50),
            chat_title="test2",
            video_note=MockVideoNote(
                mime_type="video/mp4",
                date=datetime(2019, 7, 25, 14, 53, 50),
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(-123, message,
                                 message.video_note, "video_note")
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test2/2019_07/6 - video_note_2019-07-25T14:53:50.mp4"
                ),
                "mp4",
            ),
            result,
        )

    @mock.patch("media_downloader.app.save_path", new=MOCK_DIR)
    @mock.patch("media_downloader.asyncio.sleep", return_value=None)
    @mock.patch("media_downloader.logger")
    @mock.patch("media_downloader.RETRY_TIME_OUT", new=1)
    @mock.patch("media_downloader._is_exist", new=is_exist)
    def test_download_media(self, mock_logger, patched_time_sleep):

        client = MockClient()
        message = MockMessage(
            id=5,
            media=True,
            video=MockVideo(
                file_name="sample_video.mp4",
                mime_type="video/mp4",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message, ["video", "photo"], {"video": ["mp4"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)

        message = MockMessage(
            id=5,
            media=False,
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message, ["video", "photo"], {"video": ["mp4"]}
            )
        )
        self.assertEqual(DownloadStatus.SkipDownload, result)

        message_1 = MockMessage(
            id=6,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_1, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)

        # Test re-fetch message success
        message_2 = MockMessage(
            id=7,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_2, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)
        mock_logger.warning.assert_called_with(
            "Message[{}]: file reference expired, refetching...", 7
        )

        # Test re-fetch message failure
        message_3 = MockMessage(
            id=8,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_3, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)
        mock_logger.error.assert_called_with(
            "Message[{}]: file reference expired for 3 retries, download skipped.",
            8,
        )

        # Test other exception
        message_4 = MockMessage(
            id=9,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_4, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)

        # Check no media
        message_5 = MockMessage(
            id=10,
            media=None,
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_5, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.SkipDownload, result)

        # Test timeout
        message_6 = MockMessage(
            id=11,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_6, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)
        mock_logger.error.assert_called_with(
            "Message[{}]: Timing out after 3 reties, download skipped.", 11
        )

        # Test FloodWait 420
        message_7 = MockMessage(
            id=420,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_7, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)
        mock_logger.warning.assert_called_with(
            "Message[{}]: FlowWait {}", 420, 420)

        # Test other Exception
        message_8 = MockMessage(
            id=421,
            media=True,
            video=MockVideo(
                file_name="sample_video.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_8, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)

        # Test other Exception
        message_9 = MockMessage(
            id=422,
            media=True,
            video=MockVideo(
                file_name="422 - exception.mov",
                mime_type="video/mov",
            ),
        )
        result = self.loop.run_until_complete(
            async_download_media(
                client, message_9, ["video", "photo"], {"video": ["all"]}
            )
        )
        self.assertEqual(DownloadStatus.FailedDownload, result)

    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.asyncio.Queue.put")
    def test_download_task(self, moc_put):
        rest_app(MOCK_CONF)
        client = MockClient()
        app.chat_download_config[8654123].download_filter = "id != 1213"
        self.loop.run_until_complete(download_all_chat(
            client))
        moc_put.assert_called()

    def test_can_download(self):
        file_formats = {
            "audio": ["mp3"],
            "video": ["mp4"],
            "document": ["all"],
        }
        result = _can_download("audio", file_formats, "mp3")
        self.assertEqual(result, True)

        result1 = _can_download("audio", file_formats, "ogg")
        self.assertEqual(result1, False)

        result2 = _can_download("document", file_formats, "pdf")
        self.assertEqual(result2, True)

        result3 = _can_download("document", file_formats, "epub")
        self.assertEqual(result3, True)

    def test_is_exist(self):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        result = _is_exist(os.path.join(this_dir, "__init__.py"))
        self.assertEqual(result, True)

        result1 = _is_exist(os.path.join(this_dir, "init.py"))
        self.assertEqual(result1, False)

        result2 = _is_exist(this_dir)
        self.assertEqual(result2, False)

    @mock.patch("media_downloader.RETRY_TIME_OUT", new=1)
    @mock.patch("media_downloader.os.path.getsize", new=os_get_file_size)
    @mock.patch("media_downloader.os.remove", new=os_remove)
    @mock.patch("media_downloader._is_exist", new=is_exist)
    def test_issues_311(self):
        # see https://github.com/Dineshkarthik/telegram_media_downloader/issues/311
        rest_app(MOCK_CONF)

        client = MockClient()
        # 1. test `TimeOutError`
        message = MockMessage(
            id=311,
            media=True,
            video=MockVideo(
                file_name="failed_down.mp4",
                mime_type="video/mp4",
                file_size=1024,
            ),
        )

        media_size = getattr(message.video, "file_size")
        self.assertEqual(media_size, 1024)

        res = self.loop.run_until_complete(
            async_download_media(
                client, message, ["video", "photo"], {"video": ["mp4"]}
            )
        )
        self.assertEqual(res, DownloadStatus.FailedDownload)

        # 2. test sucess download
        rest_app(MOCK_CONF)
        message = MockMessage(
            id=311,
            media=True,
            video=MockVideo(
                file_name="sucess_down.mp4",
                mime_type="video/mp4",
                file_size=1024,
            ),
        )

        res = self.loop.run_until_complete(
            async_download_media(
                client, message, ["video", "photo"], {"video": ["mp4"]}
            )
        )

        self.assertEqual(res, DownloadStatus.SuccessDownload)

        rest_app(MOCK_CONF)
        # 3. test already download
        message = MockMessage(
            id=311,
            media=True,
            video=MockVideo(
                file_name="sucess_exist_down.mp4",
                mime_type="video/mp4",
                file_size=1024,
            ),
        )

        res = self.loop.run_until_complete(
            async_download_media(
                client, message, ["video", "photo"], {"video": ["mp4"]}
            )
        )

        self.assertEqual(res, DownloadStatus.SkipDownload)

    @mock.patch("media_downloader.asyncio.ProactorEventLoop.run_forever", new=raise_keyboard_interrupt)
    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.RETRY_TIME_OUT", new=1)
    @mock.patch("media_downloader.logger")
    def test_main(self, mock_logger):
        rest_app(MOCK_CONF)

        main()

        mock_logger.success.assert_called_with(
            "Updated last read message_id to config file,total download {}, total upload file {}", 0, 0)
        
    @mock.patch("media_downloader.app.pre_run", new=raise_keyboard_interrupt)
    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.RETRY_TIME_OUT", new=1)
    @mock.patch("media_downloader.logger")
    def test_keyboard_interrupt(self, mock_logger):
        rest_app(MOCK_CONF)

        main()

        mock_logger.info.assert_any_call(
            "KeyboardInterrupt!")
        mock_logger.success.assert_called_with(
            "Updated last read message_id to config file,total download {}, total upload file {}", 0, 0)

    @mock.patch("media_downloader.app.pre_run", new=raise_exception)
    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.RETRY_TIME_OUT", new=1)
    @mock.patch("media_downloader.logger")
    def test_other_exception(self, mock_logger):
        rest_app(MOCK_CONF)

        main()

        mock_logger.success.assert_called_with(
            "Updated last read message_id to config file,total download {}, total upload file {}", 0, 0)
        
    
    @mock.patch("media_downloader._load_config", new=load_config)
    @mock.patch("media_downloader.logger")
    def test_check_config(self, mock_logger):
        _check_config()
        mock_logger.error.assert_called_with(
            "load config error: error load config")

    def test_check_config_suc(self):
        app.update_config()
        self.assertEqual(_check_config(), True)

    @mock.patch("media_downloader.queue", new=MyQueue)
    @mock.patch("media_downloader.app.set_download_id", new=new_set_download_id)
    def test_worker(self):
        rest_app(MOCK_CONF)
        client = MockClient()
        self.loop.run_until_complete(worker(client))

        self.assertEqual(app.chat_download_config[8654123].last_read_message_id, 7)
        self.assertEqual(app.chat_download_config[8654123].downloaded_ids, [7])

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()
        config_test = os.path.join(os.path.abspath("."), "config_test.yaml")
        data_test = os.path.join(os.path.abspath("."), "data_test.yaml")
        if os.path.exists(config_test):
            os.remove(config_test)
        if os.path.exists(data_test):
            os.remove(data_test)
