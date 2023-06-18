"""test app"""

import os
import sys
import unittest
from unittest import mock

import module.app
from module.app import Application, ChatDownloadConfig

sys.path.append("..")  # Adds higher directory to python modules path.


class AppTestCase(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        config_test = os.path.join(os.path.abspath("."), "config_test.yaml")
        data_test = os.path.join(os.path.abspath("."), "data_test.yaml")
        if os.path.exists(config_test):
            os.remove(config_test)
        if os.path.exists(data_test):
            os.remove(data_test)

    def test_app(self):
        app = Application("", "")
        self.assertEqual(app.save_path, os.path.join(os.path.abspath("."), "downloads"))
        self.assertEqual(app.proxy, {})
        self.assertEqual(app.restart_program, False)

        app.chat_download_config[123] = ChatDownloadConfig()
        app.chat_download_config[123].last_read_message_id = 13
        app.chat_download_config[123].failed_ids.append(6)
        app.chat_download_config[123].ids_to_retry.append(7)
        app.chat_download_config[123].downloaded_ids.append(8)
        app.chat_download_config[123].downloaded_ids.append(10)
        app.chat_download_config[123].downloaded_ids.append(13)
        app.config["chat"] = [{"chat_id": 123, "last_read_message_id": 5}]

        app.update_config(False)

        self.assertEqual(
            app.chat_download_config[123].last_read_message_id + 1,
            app.config["chat"][0]["last_read_message_id"],
        )
        self.assertEqual(
            [5, 6, 7, 9, 11, 12],
            app.app_data["chat"][0]["ids_to_retry"],
        )

    @mock.patch("__main__.__builtins__.open", new_callable=mock.mock_open)
    @mock.patch("module.app.yaml", autospec=True)
    def test_update_config(self, mock_yaml, mock_open):
        app = Application("", "")
        app.config_file = "config_test.yaml"
        app.app_data_file = "data_test.yaml"
        app.config["chat"] = [{"chat_id": 123, "last_read_message_id": 0}]
        app.update_config()
        mock_open.assert_called_with("data_test.yaml", "w", encoding="utf-8")
