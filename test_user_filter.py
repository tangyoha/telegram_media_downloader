from datetime import datetime

from module.filter import Filter, MetaData
from module.pyrogram_extension import set_meta_data
from tests.test_common import MockMessage, MockVideo
from utils.format import replace_date_time

# enter you want to test
vec_filter = [
    "file_size > 1KB && file_size <= 10MB",
]

meta = MetaData()

# enter you want to test
message = MockMessage(
    id=5,
    media=True,
    date=datetime(2022, 8, 5, 14, 35, 12),
    chat_title="test2",
    caption="enter you want to test",
    video=MockVideo(
        mime_type="video/mp4",
        file_size=1024 * 1024 * 10,
        file_name="test.mp4",
        width=1920,
        height=1080,
        duration=35,
    ),
)

set_meta_data(meta, message)

download_filter = Filter()

download_filter.set_meta_data(meta)


for filter_str in vec_filter:
    tmp_filter_str = replace_date_time(filter_str)
    print(f"{filter_str} {download_filter.exec(tmp_filter_str)}")
