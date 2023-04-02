"""Unittest module for media downloader."""
import os
import sys
import unittest
from unittest.mock import patch

from utils.format import (
    extract_info_from_link,
    format_byte,
    get_byte_from_str,
    replace_date_time,
    truncate_filename,
)

sys.path.append("..")  # Adds higher directory to python modules path.


class FormatTestCase(unittest.TestCase):
    def test_format_byte(self):
        byte_list = [
            "KB",
            "MB",
            "GB",
            "TB",
            "PB",
            "EB",
            "ZB",
            "YB",
            "BB",
            "NB",
            "DB",
            "CB",
        ]

        self.assertEqual(format_byte(0.1), "0.8b")
        self.assertEqual(format_byte(1), "1B")

        for i, value in enumerate(byte_list):
            self.assertEqual(format_byte(pow(1024, i + 1)), "1.0" + value)

        try:
            format_byte(-1)
        except Exception as e:
            self.assertEqual(isinstance(e, ValueError), True)

    def test_replace_date_time(self):
        self.assertEqual(
            replace_date_time(""),
            "",
        )

        # split by '.'
        self.assertEqual(
            replace_date_time("xxxxx 2020.03.08 xxxxxxxxx"),
            "xxxxx 2020-03-08 00:00:00 xxxxxxxxx",
        )

        # split by '-'
        self.assertEqual(
            replace_date_time("xxxxx 2020-03-08 xxxxxxxxxxxx"),
            "xxxxx 2020-03-08 00:00:00 xxxxxxxxxxxx",
        )

        # split by '/'
        self.assertEqual(
            replace_date_time("xasd as 2020/03/08 21321fszv"),
            "xasd as 2020-03-08 00:00:00 21321fszv",
        )

        # more different date
        self.assertEqual(
            replace_date_time("xxxxx 2020.03.08 2020.03.09 14:51 xxxxxxxxx"),
            "xxxxx 2020-03-08 00:00:00 2020-03-09 14:51:00 xxxxxxxxx",
        )

        # more space
        self.assertEqual(
            replace_date_time("xxxxx 2020.03.08 2020.03.09      14:51 xxxxxxxxx"),
            "xxxxx 2020-03-08 00:00:00 2020-03-09 14:51:00 xxxxxxxxx",
        )

        # more date format
        self.assertEqual(
            replace_date_time("xasd as 2020/03 21321fszv"),
            "xasd as 2020-03-01 00:00:00 21321fszv",
        )
        self.assertEqual(
            replace_date_time("xasd as 2020-03 21321fszv"),
            "xasd as 2020-03-01 00:00:00 21321fszv",
        )
        self.assertEqual(
            replace_date_time("xasd as 2020.03 21321fszv"),
            "xasd as 2020-03-01 00:00:00 21321fszv",
        )

    def test_get_byte_from_str(self):
        # B
        self.assertEqual(get_byte_from_str("2B"), 2)
        # KB
        self.assertEqual(get_byte_from_str("2KB"), 2 * 1024)
        self.assertEqual(get_byte_from_str("1024KB"), 1024 * 1024)
        self.assertEqual(get_byte_from_str("2024KB"), 2024 * 1024)
        self.assertEqual(get_byte_from_str("4000KB"), 4000 * 1024)

        # MB
        self.assertEqual(get_byte_from_str("2MB"), 2 * 1024 * 1024)
        self.assertEqual(get_byte_from_str("1024MB"), 1024 * 1024 * 1024)

        # GB
        self.assertEqual(get_byte_from_str("2GB"), 2 * 1024 * 1024 * 1024)

        # TB
        self.assertEqual(get_byte_from_str("2TB"), 2 * 1024 * 1024 * 1024 * 1024)
        self.assertEqual(get_byte_from_str("1024TB"), 1024 * 1024 * 1024 * 1024 * 1024)

        # more str
        self.assertEqual(get_byte_from_str("2BW"), 2)
        self.assertEqual(get_byte_from_str("2WBW"), None)

        self.assertEqual(get_byte_from_str("2CB"), None)

    def test_extract_info_from_link(self):
        link1 = "https://t.me/"
        username, message_id = extract_info_from_link(link1)
        self.assertEqual(username, None)
        self.assertEqual(message_id, None)

        link1 = "https://t.me/username/1234"
        username, message_id = extract_info_from_link(link1)
        self.assertEqual(username, "username")
        self.assertEqual(message_id, 1234)

        link2 = "https://t.me/username"
        username, message_id = extract_info_from_link(link2)
        self.assertEqual(username, "username")
        self.assertEqual(message_id, None)

        link3 = "https://t.me/c/213213/91011"
        username, message_id = extract_info_from_link(link3)
        self.assertEqual(username, -100213213)
        self.assertEqual(message_id, 91011)


class TestTruncateFilename(unittest.TestCase):
    def test_truncate_filename(self):
        test_cases = [
            ("testfile.txt", 240, "testfile.txt"),
            ("testfile.txt", 5, "t.txt"),
            ("a" * 240 + ".txt", 240, "a" * 236 + ".txt"),
            ("a" * 241 + ".txt", 240, "a" * 236 + ".txt"),
        ]

        for path, limit, expected in test_cases:
            self.assertEqual(truncate_filename(path, limit), expected)

    @unittest.skipIf(sys.platform.startswith("win"), "requires Unix-based system")
    def test_linux_filename_too_long(self):
        long_filename = "a" * 265 + ".txt"
        with self.assertRaises(OSError):
            with open(long_filename, "w") as f:
                f.write("test")

        long_filename = "a" * 265 + ".txt"
        long_filename = truncate_filename(long_filename)
        try:
            with open(long_filename, "w") as f:
                f.write("test")
            os.remove(long_filename)
        except Exception:
            self.assertEqual(False, True)

    @unittest.skipIf(not sys.platform.startswith("win"), "requires Windows system")
    def test_windows_filename_too_long(self):
        long_filename = "a" * 265 + ".txt"
        with self.assertRaises(OSError):
            with open(long_filename, "w") as f:
                f.write("test")

        long_filename = "a" * 265 + ".txt"
        long_filename = truncate_filename(long_filename)
        try:
            with open(long_filename, "w") as f:
                f.write("test")
            os.remove(long_filename)
        except Exception:
            self.assertEqual(False, True)

    @patch("builtins.open", unittest.mock.mock_open())
    def test_file_creation(self):
        file_name = "a" * 240 + ".txt"
        truncated_file_name = truncate_filename(file_name)

        with open(truncated_file_name, "w") as f:
            f.write("test")

        open.assert_called_once_with(truncated_file_name, "w")
