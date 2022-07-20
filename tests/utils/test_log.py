"""Unittest module for log handlers."""
import os
import sys
import unittest

import mock

sys.path.append("..")  # Adds higher directory to python modules path.
from utils.log import LogFilter


class MockLog:
    """
    Mock logs.
    """

    def __init__(self, **kwargs):
        self.funcName = kwargs["funcName"]


class MetaTestCase(unittest.TestCase):
    def test_log_filter(self):
        result = LogFilter().filter(MockLog(funcName="invoke"))
        self.assertEqual(result, False)

        result1 = LogFilter().filter(MockLog(funcName="get_file"))
        self.assertEqual(result1, True)

        result2 = LogFilter().filter(MockLog(funcName="Synced"))
        self.assertEqual(result2, True)
