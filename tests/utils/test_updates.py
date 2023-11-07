"""Unittest module for update checker."""
import json
import sys
import unittest

import mock

sys.path.append("..")  # Adds higher directory to python modules path.
from utils.updates import check_for_updates, get_latest_release


class FakeHTTPSConnection:
    def __init__(self, status):
        self.status = status

    def request(self, *args, **kwargs):
        pass

    def getresponse(self):
        return FakeHTTPSResponse(self.status)


class FakeHTTPSResponse:
    def __init__(self, status):
        self.status = status

    def read(self):
        if self.status == 200:
            return b'{"name":"v0.0.0 2022-03-02","tag_name":"v0.0.0", "html_url":"https://github.com/tangyoha/telegram_media_downloader/releases/tag/v0.0.0"}'
        else:
            return b"{error}"


class MocResponse:
    def __init__(self, text: str):
        self.text = text


def new_request_get(*args, **kwargs):
    return MocResponse('{"tag_name":"v0.0.0"}')


import unittest
from unittest.mock import MagicMock, patch

from utils import __version__
from utils.updates import check_for_updates, get_latest_release


class TestUpdates(unittest.TestCase):
    @patch("requests.get")
    def test_get_latest_release(self, mock_get):
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "name": "v0.0.0 2022-03-02",
                "tag_name": "v0.0.0",
                "html_url": "https://github.com/tangyoha/telegram_media_downloader/releases/tag/v0.0.0",
            }
        )
        mock_get.return_value = mock_response

        # Call the function with a test proxy_config
        proxy_config = {
            "scheme": "http",
            "hostname": "localhost",
            "port": "8080",
            "username": "user",
            "password": "pass",
        }
        result = get_latest_release(proxy_config)

        # Check the result
        self.assertEqual(result["name"], "v0.0.0 2022-03-02")
        self.assertEqual(result["tag_name"], "v0.0.0")
        self.assertEqual(
            result["html_url"],
            "https://github.com/tangyoha/telegram_media_downloader/releases/tag/v0.0.0",
        )

    @patch("requests.get")
    def test_get_latest_release_same_version(self, mock_get):
        # Mock the response from requests.get
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "name": f"v{__version__} 2022-03-02",
                "tag_name": f"v{__version__}",
                "html_url": "https://github.com/tangyoha/telegram_media_downloader/releases/tag/v0.0.0",
            }
        )
        mock_get.return_value = mock_response

        # Call the function with a test proxy_config
        proxy_config = {
            "scheme": "http",
            "hostname": "localhost",
            "port": "8080",
            "username": "user",
            "password": "pass",
        }
        result = get_latest_release(proxy_config)

        # Check the result
        self.assertEqual(result, {})

    @patch("requests.get")
    def test_get_latest_release_exception(self, mock_get):
        # Mock the response from requests.get to raise an exception
        mock_get.side_effect = Exception("Test exception")

        # Call the function with a test proxy_config
        proxy_config = {
            "scheme": "http",
            "hostname": "localhost",
            "port": "8080",
            "username": "user",
            "password": "pass",
        }
        result = get_latest_release(proxy_config)

        # Check the result
        self.assertEqual(result, {})

    @patch("utils.updates.get_latest_release")
    @patch("utils.updates.Console")
    def test_check_for_updates(self, mock_console, mock_get_latest_release):
        # Mock the response from get_latest_release
        mock_get_latest_release.return_value = {
            "name": "v0.0.0 2022-03-02",
            "tag_name": "v0.0.0",
            "html_url": "https://github.com/tangyoha/telegram_media_downloader/releases/tag/v0.0.0",
        }

        # Call the function with a test proxy_config
        proxy_config = {
            "scheme": "http",
            "hostname": "localhost",
            "port": "8080",
            "username": "user",
            "password": "pass",
        }
        check_for_updates(proxy_config)

        # Check the console output
        mock_console.return_value.print.assert_called_once()
