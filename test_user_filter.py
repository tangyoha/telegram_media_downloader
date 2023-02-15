

from datetime import datetime
from tests.test_common import MockMessage, MockVideo
from module.filter import Filter, MetaData
from utils.format import replace_date_time


# custom
vec_filter = [
    "file_size > 1KB && file_size <= 10MB",
    "(file_size > 1KB && file_size <= 10MB) and caption == r'.*#我的最爱.*'",
    "(file_size > 1KB && file_size <= 10MB) and caption == r'.*三体.*'",
    "(file_size > 1KB && file_size <= 10MB) and caption != r'.*女主播.*'",
    # \. eq string .
    "(file_size > 1KB && file_size <= 10MB) and caption != r'test\.mp4'",
    "(file_size > 1KB && file_size <= 10MB) and file_name == r'test\.mp4'",
    "(file_size > 1KB && file_size <= 10MB) and file_name != r'test\-mp4'",
]

meta = MetaData()

message = MockMessage(
    id=5,
    media=True,
    date=datetime(2022, 8, 5, 14, 35, 12),
    chat_title="test2",
    caption="#书籍 #我的最爱 #三体",
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

download_filter = Filter()

download_filter.set_meta_data(meta)


for filter_str in vec_filter:
    tmp_filter_str = replace_date_time(filter_str)
    print(f"{filter_str} {download_filter.exec(tmp_filter_str)}")
