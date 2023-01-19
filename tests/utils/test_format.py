"""Unittest module for media downloader."""
import sys
import unittest

from utils.format import format_byte

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
