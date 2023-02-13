"""Unittest module for media downloader."""
import sys
import unittest

from utils.format import format_byte, replace_date_time

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
