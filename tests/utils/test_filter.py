"""Unittest module for media downloader."""
import sys
import unittest
from datetime import datetime

from tests.test_common import (
    Chat,
    Date,
    MockAudio,
    MockDocument,
    MockMessage,
    MockPhoto,
    MockVideo,
    MockVideoNote,
    MockVoice,
)
from utils.filter import Filter, MetaData
from utils.format import replace_date_time

sys.path.append("..")  # Adds higher directory to python modules path.


def filter_exec(download_filter: Filter, filter_str: str) -> bool:
    filter_str = replace_date_time(filter_str)
    return download_filter.exec(filter_str)


class FilterTestCase(unittest.TestCase):
    def test_string_filter(self):
        download_filter = Filter()
        self.assertRaises(ValueError, filter_exec, download_filter, "213")

        meta = MetaData()

        message = MockMessage(
            id=5,
            media=True,
            date=datetime(2022, 8, 5, 14, 35, 12),
            chat_title="test2",
            caption="",
            video=MockVideo(
                mime_type="video/mp4",
                file_size=1024 * 1024 * 10,
                file_name="test.mp4",
                width=1920,
                height=1080,
                duration=35,
            ),
        )

        meta.get_meta_data(message)

        self.assertEqual(meta.message_id, 5)
        self.assertEqual(meta.message_date, datetime(2022, 8, 5, 14, 35, 12))
        self.assertEqual(meta.message_caption, "")
        self.assertEqual(meta.media_file_size, 1024 * 1024 * 10)
        self.assertEqual(meta.media_width, 1920)
        self.assertEqual(meta.media_height, 1080)
        self.assertEqual(meta.media_file_name, "test.mp4")
        self.assertEqual(meta.media_duration, 35)

        download_filter.set_meta_data(meta)

        self.assertEqual(filter_exec(download_filter, "media_file_size == 1"), False)
        self.assertEqual(filter_exec(download_filter, "media_file_size > 1024"), True)

        # str
        self.assertEqual(
            filter_exec(download_filter, "media_file_name == 'test.mp4'"), True
        )
        self.assertEqual(
            filter_exec(download_filter, "media_file_name == 'test2.mp4'"), False
        )
        # re str
        self.assertEqual(
            filter_exec(download_filter, "media_file_name == r'test.*mp4'"), True
        )
        self.assertEqual(
            filter_exec(download_filter, "media_file_name == r'test2.*mp4'"), False
        )
        self.assertEqual(
            filter_exec(download_filter, "media_file_name != r'test2.*mp4'"), True
        )
        self.assertEqual(
            filter_exec(download_filter, "media_file_name != r'test2.*mp4'"), True
        )

        # int
        self.assertEqual(filter_exec(download_filter, "media_duration > 60"), False)
        self.assertEqual(filter_exec(download_filter, "media_duration <= 60"), True)
        self.assertEqual(
            filter_exec(
                download_filter, "media_width >= 1920 and media_height >= 1080"
            ),
            True,
        )
        self.assertEqual(
            filter_exec(download_filter, "media_width >= 2560 && media_height >= 1440"),
            False,
        )
        self.assertEqual(
            filter_exec(
                download_filter,
                "media_width >= 2560 && media_height >= 1440 or media_file_name == 'test.mp4'",
            ),
            True,
        )

        # datetime
        # 2020.03
        self.assertEqual(
            filter_exec(
                download_filter, "message_date >= 2022.03 and message_date <= 2022.08"
            ),
            False,
        )
        self.assertEqual(
            filter_exec(
                download_filter, "message_date >= 2022.03 and message_date <= 2022.09"
            ),
            True,
        )

        # 2020.03.04
        self.assertEqual(
            filter_exec(
                download_filter,
                "message_date >= 2022.03.04 and message_date <= 2022.03.08",
            ),
            False,
        )
        self.assertEqual(
            filter_exec(
                download_filter,
                "message_date >= 2022.03.04 and message_date <= 2022.08.06",
            ),
            True,
        )

        # 2020.03.04 14:50
        self.assertEqual(
            filter_exec(
                download_filter,
                "message_date >= 2022.03.04 14:50 and message_date <= 2022.03.08",
            ),
            False,
        )
        self.assertEqual(
            filter_exec(
                download_filter,
                "message_date >= 2022.03.04 and message_date <= 2022.08.05 14:36",
            ),
            True,
        )

        # 2020.03.04 14:50:15
        self.assertEqual(
            filter_exec(
                download_filter,
                "message_date >= 2022.03.04 14:50:15 and message_date <= 2022.03.08",
            ),
            False,
        )
        self.assertEqual(
            filter_exec(
                download_filter,
                "message_date >= 2022.03.04 14:50:15 and message_date <= 2022.08.05 14:35:12",
            ),
            True,
        )

        # test not exist value
        self.assertEqual(
            filter_exec(
                download_filter,
                "message_date >= 2022.03.04 && message_date <= 2022.08.06 && not_exist == True",
            ),
            True,
        )
