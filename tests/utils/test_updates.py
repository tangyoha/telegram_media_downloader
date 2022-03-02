"""Unittest module for update checker."""
import os
import sys
import unittest

import mock
from rich.markdown import Markdown

sys.path.append("..")  # Adds higher directory to python modules path.
from utils.updates import check_for_updates


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
        return b'{"name":"v0.0.0 2022-03-02","tag_name":"v0.0.0", "html_url":"https://github.com/Dineshkarthik/telegram_media_downloader/releases/tag/v0.0.0"}'


class UpdatesTestCase(unittest.TestCase):
    @mock.patch(
        "utils.updates.http.client.HTTPSConnection",
        new=mock.MagicMock(return_value=FakeHTTPSConnection(200)),
    )
    @mock.patch("utils.updates.__version__", new="0.0.1")
    @mock.patch("utils.updates.Console")
    @mock.patch("utils.updates.Markdown")
    def test_update(self, mock_markdown, mock_console):
        check_for_updates()
        name: str = "v0.0.0 2022-03-02"
        html_url: str = "https://github.com/Dineshkarthik/telegram_media_downloader/releases/tag/v0.0.0"
        expected_message: str = (
            f"## New versionof Telegram-Media-Downloader is available - {name}\n"
            "You are using an outdated version v0.0.1 please pull in the changes using `git pull` or download the latest release.\n\n"
            f"Find more details about the latest release here - {html_url}"
        )
        mock_markdown.assert_called_with(expected_message)
        mock_console.return_value.print.assert_called_once()
