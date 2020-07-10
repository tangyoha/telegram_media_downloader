"""Unittest module for media downloader."""
import os
import copy
import logging
import unittest

import mock
import pytest
import asyncio

from media_downloader import (
    _get_media_meta,
    download_media,
    update_config,
    begin_import,
    process_messages,
)

MOCK_DIR = "/root/project"
MOCK_CONF = {
    "api_id": 123,
    "api_hash": "hasw5Tgawsuj67",
    "last_read_message_id": 0,
    "chat_id": 8654123,
    "media_types": ["audio", "voice"],
    "file_formats": {"audio": ["all"], "voice": ["all"]},
}


class MockMessage:
    def __init__(self, **kwargs):
        self.message_id = kwargs.get("id")
        self.media = kwargs.get("media")
        self.audio = kwargs.get("audio", None)
        self.document = kwargs.get("document", None)
        self.photo = kwargs.get("photo", None)
        self.video = kwargs.get("video", None)
        self.voice = kwargs.get("voice", None)


class MockAudio:
    def __init__(self, **kwargs):
        self.file_ref = kwargs["file_ref"]
        self.file_name = kwargs["file_name"]
        self.mime_type = kwargs["mime_type"]


class MockDocument:
    def __init__(self, **kwargs):
        self.file_ref = kwargs["file_ref"]
        self.file_name = kwargs["file_name"]
        self.mime_type = kwargs["mime_type"]


class MockPhoto:
    def __init__(self, **kwargs):
        self.file_ref = kwargs["file_ref"]
        self.date = kwargs["date"]


class MockVoice:
    def __init__(self, **kwargs):
        self.file_ref = kwargs["file_ref"]
        self.mime_type = kwargs["mime_type"]
        self.date = kwargs["date"]


class MockVideo:
    def __init__(self, **kwargs):
        self.file_ref = kwargs["file_ref"]
        self.mime_type = kwargs["mime_type"]


async def async_get_media_meta(message_media, _type):
    result = await _get_media_meta(message_media, _type)
    return result


async def async_download_media(client, message, media_types, file_formats):
    result = await download_media(client, message, media_types, file_formats)
    return result


async def async_begin_import(conf, pagination_limit):
    result = await begin_import(conf, pagination_limit)
    return result


async def mock_process_message(*args, **kwargs):
    return 5


async def async_process_messages(client, messages, media_types, file_formats):
    result = await process_messages(
        client, messages, media_types, file_formats
    )
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

    async def iter_history(self, *args, **kwargs):
        items = [
            MockMessage(
                id=1213,
                media=True,
                voice=MockVoice(
                    file_ref="AwADBQADbwAD2oTRVeHe5eXRFftfAg",
                    mime_type="audio/ogg",
                    date=1564066430,
                ),
            ),
            MockMessage(id=1214, media=False, text="test message 1",),
            MockMessage(id=1215, media=False, text="test message 2",),
            MockMessage(id=1216, media=False, text="test message 3",),
        ]
        for item in items:
            yield item

    async def download_media(self, *args, **kwargs):
        assert "AwADBQADbwAD2oTRVeHe5eXRFftfAg", args[0]
        assert "/root/project/voice/voice_2019-07-25T14:53:50.ogg", kwargs[
            "file_name"
        ]
        return kwargs["file_name"]


class MediaDownloaderTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.get_event_loop()

    @mock.patch("media_downloader.THIS_DIR", new=MOCK_DIR)
    def test_get_media_meta(self):
        # Test Voice notes
        message = MockMessage(
            id=1,
            media=True,
            voice=MockVoice(
                file_ref="AwADBQADbwAD2oTRVeHe5eXRFftfAg",
                mime_type="audio/ogg",
                date=1564066430,
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(message.voice, "voice")
        )

        self.assertEqual(
            (
                "AwADBQADbwAD2oTRVeHe5eXRFftfAg",
                "/root/project/voice/voice_2019-07-25T14:53:50.ogg",
                "ogg",
            ),
            result,
        )

        # Test photos
        message = MockMessage(
            id=2,
            media=True,
            photo=MockPhoto(
                file_ref="AgADBQAD5KkxG_FPQValJzQsJPyzhHcC", date=1565015712
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(message.photo, "photo")
        )
        self.assertEqual(
            ("AgADBQAD5KkxG_FPQValJzQsJPyzhHcC", "/root/project/photo/", None),
            result,
        )

        # Test Documents
        message = MockMessage(
            id=3,
            media=True,
            document=MockDocument(
                file_ref="AQADAgADq7LfMgAEIdy5DwAE4w4AAwI",
                file_name="sample_document.pdf",
                mime_type="application/pdf",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(message.document, "document")
        )
        self.assertEqual(
            (
                "AQADAgADq7LfMgAEIdy5DwAE4w4AAwI",
                "/root/project/document/sample_document.pdf",
                "pdf",
            ),
            result,
        )

        # Test audio
        message = MockMessage(
            id=4,
            media=True,
            audio=MockAudio(
                file_ref="AQADAgADq7LfMgAEIdy5DwAE5Q4AAgEC",
                file_name="sample_audio.mp3",
                mime_type="audio/mp3",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(message.audio, "audio")
        )
        self.assertEqual(
            (
                "AQADAgADq7LfMgAEIdy5DwAE5Q4AAgEC",
                "/root/project/audio/sample_audio.mp3",
                "mp3",
            ),
            result,
        )

        # Test Video
        message = MockMessage(
            id=5,
            media=True,
            video=MockVideo(
                file_ref="CQADBQADeQIAAlL60FUCNMBdK8OjlAI",
                mime_type="video/mp4",
            ),
        )
        result = self.loop.run_until_complete(
            async_get_media_meta(message.video, "video")
        )
        self.assertEqual(
            ("CQADBQADeQIAAlL60FUCNMBdK8OjlAI", "/root/project/video/", "mp4"),
            result,
        )

    @mock.patch("media_downloader.THIS_DIR", new=MOCK_DIR)
    def test_download_media(self):
        client = MockClient()
        message = MockMessage(
            id=5,
            media=True,
            video=MockVideo(
                file_ref="CQADBQADeQIAAlL60FUCNMBdK8OjlAI",
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
                file_ref="CQADBQADeQIAAlL60FUCNMBdK8OjlAI",
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

    @mock.patch("__main__.__builtins__.open", new_callable=mock.mock_open)
    @mock.patch("media_downloader.yaml", autospec=True)
    def test_update_config(self, mock_yaml, mock_open):
        conf = {"api_id": 123, "api_hash": "hasw5Tgawsuj67"}
        update_config(conf)
        mock_open.assert_called_with("config.yaml", "w")
        mock_yaml.dump.assert_called_with(
            conf, mock.ANY, default_flow_style=False
        )

    @mock.patch("media_downloader.pyrogram.Client", new=MockClient)
    @mock.patch("media_downloader.process_messages", new=mock_process_message)
    def test_begin_import(self):
        result = self.loop.run_until_complete(async_begin_import(MOCK_CONF, 3))
        conf = copy.deepcopy(MOCK_CONF)
        conf["last_read_message_id"] = 5
        self.assertDictEqual(result, conf)

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
                            file_ref="AwADBQADbwAD2oTRVeHe5eXRFftfAg",
                            mime_type="audio/ogg",
                            date=1564066430,
                        ),
                    ),
                    MockMessage(id=1214, media=False, text="test message 1",),
                    MockMessage(id=1215, media=False, text="test message 2",),
                    MockMessage(id=1216, media=False, text="test message 3",),
                ],
                ["voice", "photo"],
                {"audio": ["all"], "voice": ["all"]},
            )
        )
        self.assertEqual(result, 1216)

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()
