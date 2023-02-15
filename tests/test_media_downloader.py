"""Unittest module for media downloader."""
import asyncio
import os
import platform
import unittest
from datetime import datetime

import mock
import pyrogram

from media_downloader import (
    _can_download,
    _get_media_meta,
    _is_exist,
    app,
    begin_import,
    download_media,
    exec_main,
    main,
    process_messages,
)

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
    "last_read_message_id": 0,
    "chat_id": 8654123,
    "ids_to_retry": [1, 2],
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


def rest_app(conf: dict):
    app.reset()
    app.config_file = "config_test.yaml"
    app.app_data_file = "data_test.yaml"
    app.assign_config(conf)


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


async def async_get_media_meta(message, message_media, _type):
    result = await _get_media_meta(message, message_media, _type)
    return result


async def async_download_media(client, message, media_types, file_formats):
    result = await download_media(client, message, media_types, file_formats)
    return result


async def async_begin_import(pagination_limit):
    result = await begin_import(pagination_limit)
    return result


async def mock_process_message(*args, **kwargs):
    return 5


async def async_process_messages(client, messages, media_types, file_formats):
    result = await process_messages(client, messages, media_types, file_formats)
    return result


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
            async_get_media_meta(message, message.voice, "voice")
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
            async_get_media_meta(message, message.photo, "photo")
        )
        self.assertEqual(
            (
                platform_generic_path("/root/project/test2/2019_08/2 - ADAVKJYIFV.jpg"),
                "jpg",
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
            async_get_media_meta(message, message.photo, "photo")
        )
        self.assertEqual(
            (
                platform_generic_path(
                    "/root/project/test2/2019_08/2 - #home #book - ADAVKJYIFV.jpg"
                ),
                "jpg",
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
            async_get_media_meta(message, message.document, "document")
        )
        self.assertEqual(
            (
                platform_generic_path("/root/project/test2/0/3 - sample_document.pdf"),
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
            async_get_media_meta(message, message.document, "document")
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
            async_get_media_meta(message, message.audio, "audio")
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
            async_get_media_meta(message, message.video, "video")
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
            async_get_media_meta(message, message.video, "video")
        )
        self.assertEqual(
            (
                platform_generic_path("/root/project/test2/2022_08/5 - test.mp4"),
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
            async_get_media_meta(message, message.video, "video")
        )

        print(app.chat_id)
        self.assertEqual(
            (
                platform_generic_path("/root/project/8654123/2022_08/5 - test.mp4"),
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
            async_get_media_meta(message, message.video_note, "video_note")
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
        self.assertEqual(5, result)

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
        self.assertEqual(6, result)

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
        self.assertEqual(7, result)
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
        self.assertEqual(8, result)
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
        self.assertEqual(9, result)

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
        self.assertEqual(10, result)

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
        self.assertEqual(11, result)
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
        self.assertEqual(420, result)
        mock_logger.warning.assert_called_with("Message[{}]: FlowWait {}", 420, 420)
        self.assertEqual(app.failed_ids.count(420), 1)

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
        self.assertEqual(421, result)
        self.assertEqual(app.failed_ids.count(421), 1)

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
        self.assertEqual(422, result)
        self.assertEqual(app.failed_ids.count(422), 1)

    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.process_messages", new=mock_process_message)
    def test_begin_import(self):
        rest_app(MOCK_CONF)
        self.loop.run_until_complete(async_begin_import(1))
        self.assertEqual(5, app.last_read_message_id)

    def test_process_message(self):
        client = MockClient()
        result = self.loop.run_until_complete(
            async_process_messages(
                client,
                [
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
                ],
                ["voice", "photo"],
                {"audio": ["all"], "voice": ["all"]},
            )
        )
        self.assertEqual(result, 1216)

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

        self.loop.run_until_complete(
            async_download_media(
                client, message, ["video", "photo"], {"video": ["mp4"]}
            )
        )
        self.assertEqual(app.failed_ids, [311])
        app.update_config(False)

        self.assertEqual(app.ids_to_retry, [1, 2, 311])

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

        self.loop.run_until_complete(
            async_download_media(
                client, message, ["video", "photo"], {"video": ["mp4"]}
            )
        )

        self.assertEqual(app.failed_ids, [])

        app.update_config(False)

        self.assertEqual(app.total_download_task, 1)
        self.assertEqual(app.ids_to_retry, [1, 2])

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

        self.loop.run_until_complete(
            async_download_media(
                client, message, ["video", "photo"], {"video": ["mp4"]}
            )
        )

        self.assertEqual(app.failed_ids, [])

        app.update_config(False)

        self.assertEqual(app.total_download_task, 0)
        self.assertEqual(app.ids_to_retry, [1, 2])

    @mock.patch("media_downloader.check_for_updates", new=raise_keyboard_interrupt)
    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.process_messages", new=mock_process_message)
    @mock.patch("media_downloader.RETRY_TIME_OUT", new=1)
    @mock.patch("media_downloader.begin_import", new=async_begin_import)
    def test_keyboard_interrupt(self):
        rest_app(MOCK_CONF)
        app.failed_ids.append(3)
        app.failed_ids.append(4)

        try:
            main()
        except:
            pass

        self.assertEqual(app.ids_to_retry, [1, 2, 3, 4])

    @mock.patch("media_downloader.check_for_updates", new=raise_exception)
    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.process_messages", new=mock_process_message)
    @mock.patch("media_downloader.RETRY_TIME_OUT", new=1)
    @mock.patch("media_downloader.begin_import", new=async_begin_import)
    def test_other_exception(self):
        rest_app(MOCK_CONF)
        app.failed_ids.append(3)
        app.failed_ids.append(4)

        try:
            main()
        except:
            pass

        self.assertEqual(app.ids_to_retry, [1, 2, 3, 4])

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()
