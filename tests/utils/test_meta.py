"""Unittest module for media downloader."""
import os
import sys
import unittest

import mock

sys.path.append("..")  # Adds higher directory to python modules path.
from utils.meta import print_meta


class MetaTestCase(unittest.TestCase):
    @mock.patch("utils.meta.APP_VERSION", "test-version 1.0.0")
    @mock.patch("utils.meta.DEVICE_MODEL", "CPython X.X.X")
    @mock.patch("utils.meta.SYSTEM_VERSION", "System xx.x.xx")
    @mock.patch("media_downloader.logger")
    def test_print_meta(self, mock_logger):
        print_meta(mock_logger)
        calls = [
            mock.call.info("Device: CPython X.X.X - test-version 1.0.0"),
            mock.call.info("System: System xx.x.xx (EN)"),
        ]
        mock_logger.assert_has_calls(calls, any_order=True)
