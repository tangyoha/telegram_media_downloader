"""Unittest module for media downloader."""
import os
import sys
import unittest
from unittest.mock import patch

from utils.format import (
    create_progress_bar,
    extract_info_from_link,
    format_byte,
    get_byte_from_str,
    replace_date_time,
    truncate_filename,
    validate_title,
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
        test_cases = [
            ("https://t.me/", (None, None)),
            ("https://t.me/username/1234", ("username", 1234)),
            ("https://t.me/username", ("username", None)),
            ("https://t.me/c/213213/91011", (-100213213, 91011)),
            ("me", ("me", None)),
            ("self", ("self", None)),
        ]

        for link, expected_output in test_cases:
            result = extract_info_from_link(link)
            self.assertEqual(result, expected_output)

    def test_create_progress_bar(self):
        progress = 50
        progress_bar = create_progress_bar(progress)
        self.assertEqual(progress_bar, "█████░░░░░")

    def test_create_progress_bar_with_custom_bars(self):
        progress = 75
        total_bars = 20
        progress_bar = create_progress_bar(progress, total_bars)
        self.assertEqual(progress_bar, "███████████████░░░░░")


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
        long_filename = truncate_filename(long_filename) + ".temp"
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
        long_filename = truncate_filename(long_filename) + ".temp"
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


class TestValidateTitle(unittest.TestCase):
    def test_validate_title(self):
        test_cases = [
            ("Hello, World!", "Hello, World!"),
            ("Invalid/Title", "Invalid_Title"),
            ("File\\Name", "File_Name"),
            ("Colons:Are:Not:Allowed", "Colons_Are_Not_Allowed"),
            ("Asterisks*In*Title", "Asterisks_In_Title"),
            ("Question?Mark", "Question_Mark"),
            ('Double"Quotes', "Double_Quotes"),
            ("Less<Than", "Less_Than"),
            ("Greater>Than", "Greater_Than"),
            ("Pipe|Symbol", "Pipe_Symbol"),
            ("Multi\nLine", "Multi_Line"),
        ]

        for title, expected in test_cases:
            with self.subTest(title=title, expected=expected):
                self.assertEqual(validate_title(title), expected)

    @patch("utils.format.re.sub")
    def test_mock_re_sub(self, mock_re_sub):
        title = "Invalid/Title"
        mock_re_sub.return_value = "Mocked_Title"

        result = validate_title(title)
        self.assertEqual(result, "Mocked_Title")
        mock_re_sub.assert_called_once_with(r"[/\\:*?\"<>|\n]", "_", title)
