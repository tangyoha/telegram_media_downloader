"""Unittest module for media downloader."""
import os
import copy
import logging
import unittest

import mock
import pytest

from media_downloader import (
    _get_media_meta,
    download_media,
    update_config,
    begin_import,
)

MOCK_DIR = "/root/project"
MOCK_CONF = {
    "api_id": 123,
    "api_hash": "hasw5Tgawsuj67",
    "last_read_message_id": 0,
    "chat_id": 8654123,
    "media_types": ["audio", "voice"],
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
        self.file_id = kwargs["file_id"]
        self.file_name = kwargs["file_name"]


class MockDocument:
    def __init__(self, **kwargs):
        self.file_id = kwargs["file_id"]
        self.file_name = kwargs["file_name"]


class MockPhoto:
    def __init__(self, **kwargs):
        self.file_id = kwargs["file_id"]
        self.date = kwargs["date"]


class MockVoice:
    def __init__(self, **kwargs):
        self.file_id = kwargs["file_id"]
        self.mime_type = kwargs["mime_type"]
        self.date = kwargs["date"]


class MockVideo:
    def __init__(self, **kwargs):
        self.file_id = kwargs["file_id"]
        self.file_name = kwargs["file_name"]


class MockClient:
    def __init__(self, *args, **kwargs):
        pass

    def iter_history(self, *args, **kwargs):
        return [
            MockMessage(
                id=1213,
                media=True,
                voice=MockVoice(
                    file_id="AwADBQADbwAD2oTRVeHe5eXRFftfAg",
                    mime_type="audio/ogg",
                    date=1564066430,
                ),
            )
        ]

    def download_media(self, *args, **kwargs):
        assert "AwADBQADbwAD2oTRVeHe5eXRFftfAg", args[0]
        assert "/root/project/voice/voice_2019-07-25T14:53:50.ogg", kwargs[
            "file_name"
        ]
        return kwargs["file_name"]


class MediaDownloaderTestCase(unittest.TestCase):
    @mock.patch("media_downloader.THIS_DIR", new=MOCK_DIR)
    def test_get_media_meta(self):
        # Test Voice notes
        message = MockMessage(
            id=1,
            media=True,
            voice=MockVoice(
                file_id="AwADBQADbwAD2oTRVeHe5eXRFftfAg",
                mime_type="audio/ogg",
                date=1564066430,
            ),
        )
        result = _get_media_meta(message.voice, "voice")
        self.assertEqual(
            (
                "AwADBQADbwAD2oTRVeHe5eXRFftfAg",
                "/root/project/voice/voice_2019-07-25T14:53:50.ogg",
            ),
            result,
        )

        # Test photos
        message = MockMessage(
            id=2,
            media=True,
            photo=MockPhoto(
                file_id="AgADBQAD5KkxG_FPQValJzQsJPyzhHcC", date=1565015712
            ),
        )
        result = _get_media_meta(message.photo, "photo")
        self.assertEqual(
            ("AgADBQAD5KkxG_FPQValJzQsJPyzhHcC", "/root/project/photo/"),
            result,
        )

        # Test Documents
        message = MockMessage(
            id=3,
            media=True,
            document=MockDocument(
                file_id="AQADAgADq7LfMgAEIdy5DwAE4w4AAwI",
                file_name="sample_document.pdf",
            ),
        )
        result = _get_media_meta(message.document, "document")
        self.assertEqual(
            (
                "AQADAgADq7LfMgAEIdy5DwAE4w4AAwI",
                "/root/project/document/sample_document.pdf",
            ),
            result,
        )

        # Test audio
        message = MockMessage(
            id=4,
            media=True,
            audio=MockAudio(
                file_id="AQADAgADq7LfMgAEIdy5DwAE5Q4AAgEC",
                file_name="sample_audio.mp3",
            ),
        )
        result = _get_media_meta(message.audio, "audio")
        self.assertEqual(
            (
                "AQADAgADq7LfMgAEIdy5DwAE5Q4AAgEC",
                "/root/project/audio/sample_audio.mp3",
            ),
            result,
        )

        # Test Video
        message = MockMessage(
            id=5,
            media=True,
            video=MockVideo(
                file_id="CQADBQADeQIAAlL60FUCNMBdK8OjlAI",
                file_name="sample_video.mp4",
            ),
        )
        result = _get_media_meta(message.video, "video")
        self.assertEqual(
            (
                "CQADBQADeQIAAlL60FUCNMBdK8OjlAI",
                "/root/project/video/sample_video.mp4",
            ),
            result,
        )

    @mock.patch("media_downloader.THIS_DIR", new=MOCK_DIR)
    def test_download_media(self):
        client = MockClient()
        result = download_media(client, "8654123", "1200", ["voice", "photo"])
        self.assertEqual(1213, result)

    @mock.patch("__main__.__builtins__.open", new_callable=mock.mock_open)
    @mock.patch("media_downloader.yaml", autospec=True)
    def test_update_config(self, mock_yaml, mock_open):
        conf = {"api_id": 123, "api_hash": "hasw5Tgawsuj67"}
        update_config(conf)
        mock_open.assert_called_with("config.yaml", "w")
        mock_yaml.dump.assert_called_with(
            conf, mock.ANY, default_flow_style=False
        )

    @mock.patch("media_downloader.config", new=MOCK_CONF)
    @mock.patch("media_downloader.update_config", autospec=True)
    @mock.patch("media_downloader.download_media", return_value=21)
    @mock.patch("media_downloader.pyrogram.Client", autospec=True)
    def test_begin_import(self, mock_client, mock_download, mock_conf):
        begin_import()
        mock_client.assert_called_with(
            "media_downloader", api_id=123, api_hash="hasw5Tgawsuj67"
        )
        mock_download.assert_called_with(
            mock.ANY, 8654123, 0, ["audio", "voice"]
        )
        conf = copy.deepcopy(MOCK_CONF)
        conf["last_read_message_id"] = 22
        mock_conf.assert_called_with(conf)
