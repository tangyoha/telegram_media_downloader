"""Unittest module for media downloader."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import mock

sys.path.append("..")  # Adds higher directory to python modules path.
from utils.file_management import get_next_name, manage_duplicate_file


class FileManagementTestCase(unittest.TestCase):
    def setUp(self):
        self.this_dir = os.path.dirname(os.path.abspath(__file__))
        self.test_file = os.path.join(self.this_dir, "file-test.txt")
        self.test_file_copy_1 = os.path.join(self.this_dir, "file-test-copy1.txt")
        self.test_file_copy_2 = os.path.join(self.this_dir, "file-test-copy2.txt")
        f = open(self.test_file, "w+")
        f.write("dummy file")
        f.close()
        Path(self.test_file_copy_1).touch()
        Path(self.test_file_copy_2).touch()

    def test_get_next_name(self):
        result = get_next_name(self.test_file)
        excepted_result = os.path.join(self.this_dir, "file-test-copy3.txt")
        self.assertEqual(result, excepted_result)

    def test_manage_duplicate_file(self):
        result = manage_duplicate_file(self.test_file_copy_2)
        self.assertEqual(result, self.test_file_copy_1)

        result1 = manage_duplicate_file(self.test_file_copy_1)
        self.assertEqual(result1, self.test_file_copy_1)

    def tearDown(self):
        os.remove(self.test_file)
        os.remove(self.test_file_copy_1)
