---
name: pyrogram-telegram-bot-techniques
description: Pyrogram Telegram机器人开发技巧：解析消息链接、自定义Session超时、避免视频黑屏上传、去除消息广告。Use when working with Pyrogram, parsing Telegram message links, uploading videos, or removing advertisement content from messages.
---

# Pyrogram Telegram 机器人开发技巧

## 1. 解析 Telegram 消息链接

从 Telegram 链接中提取 chat_id、message_id 和 topic_id。

### Link 数据结构

```python
from dataclasses import dataclass
from typing import Optional, Union
from urllib.parse import parse_qs, urlparse

@dataclass
class Link:
    """Telegram Link"""
    group_id: Union[str, int, None] = None
    post_id: Optional[int] = None
    comment_id: Optional[int] = None
    topic_id: Optional[int] = None
```

### 提取链接信息

```python
def extract_info_from_link(link: str) -> Link:
    """Extract info from link"""
    if link in ("me", "self"):
        return Link(group_id=link)

    try:
        u = urlparse(link)
        paths = [p for p in u.path.split("/") if p]
        query = parse_qs(u.query)
    except ValueError:
        return Link()

    result = Link()

    if "comment" in query:
        result.group_id = paths[0]
        result.comment_id = int(query["comment"][0])
    elif len(paths) == 1 and paths[0] != "c":
        result.group_id = paths[0]
    elif len(paths) == 2:
        if paths[0] == "c":
            result.group_id = int(f"-100{paths[1]}")
        else:
            result.group_id = paths[0]
            result.post_id = int(paths[1])
    elif len(paths) == 3:
        if paths[0] == "c":
            result.group_id = int(f"-100{paths[1]}")
            result.post_id = int(paths[2])
        else:
            result.group_id = paths[0]
            result.topic_id = int(paths[1])
            result.post_id = int(paths[2])
    elif len(paths) == 4 and paths[0] == "c":
        result.group_id = int(f"-100{paths[1]}")
        result.topic_id = int(paths[2])
        result.post_id = int(paths[3])

    return result
```

### 解析链接并处理评论

```python
async def parse_link(client: pyrogram.Client, link_str: str):
    """Parse link - handles both regular messages and comments"""
    link = extract_info_from_link(link_str)
    if link.comment_id:
        # 评论链接需要获取关联群组的 ID
        chat = await client.get_chat(link.group_id)
        if chat:
            return chat.linked_chat.id, link.comment_id, link.topic_id

    return link.group_id, link.post_id, link.topic_id
```

**支持的链接格式:**
- `https://t.me/channel_name/123` - 公开频道消息
- `https://t.me/c/1234567890/123` - 私有频道消息 (自动转换为 -100 格式)
- `https://t.me/channel_name/topic_id/123` - 话题消息
- `https://t.me/channel_name/123?comment=456` - 评论消息

---

## 2. 自定义 Session 超时 (HookSession/HookClient)

继承 Pyrogram 的 Session 和 Client 类来自定义连接超时时间。

```python
import pyrogram

class HookSession(pyrogram.session.Session):
    """Hook Session with custom timeout"""

    def start_timeout(self: pyrogram.session.Session, start_timeout: int):
        """Set the start timeout for the session."""
        self.START_TIMEOUT = start_timeout


class HookClient(pyrogram.Client):
    """Hook Client with custom session timeout"""

    START_TIME_OUT = 60  # 默认 60 秒

    def __init__(self, name: str, **kwargs):
        if "start_timeout" in kwargs:
            value = kwargs.get("start_timeout")
            if value:
                self.START_TIME_OUT = value
            kwargs.pop("start_timeout")
        super().__init__(name, **kwargs)

    async def connect(self) -> bool:
        if self.is_connected:
            raise ConnectionError("Client is already connected")

        await self.load_session()

        # 使用自定义的 HookSession
        self.session = HookSession(
            self,
            await self.storage.dc_id(),
            await self.storage.auth_key(),
            await self.storage.test_mode(),
        )
        self.session.start_timeout(self.START_TIME_OUT)

        await self.session.start()
        self.is_connected = True
        return bool(await self.storage.user_id())

    async def start(self):
        is_authorized = await self.connect()
        try:
            if not is_authorized:
                await self.authorize()

            if not await self.storage.is_bot() and self.takeout:
                self.takeout_id = (
                    await self.invoke(
                        pyrogram.raw.functions.account.InitTakeoutSession()
                    )
                ).id

            await self.invoke(pyrogram.raw.functions.updates.GetState())
        except (Exception, KeyboardInterrupt):
            await self.disconnect()
            raise
        else:
            self.me = await self.get_me()
            await self.initialize()
            return self
```

**使用方法:**

```python
client = HookClient(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    start_timeout=120  # 自定义超时时间为 120 秒
)
```

---

## 3. 避免视频上传黑屏

上传视频时必须提供缩略图和视频属性，否则视频可能显示为黑屏。

### 下载视频缩略图

```python
import os
import time
import secrets
import asyncio

async def download_thumbnail(
    client: pyrogram.Client,
    temp_path: str,
    message: pyrogram.types.Message,
):
    """Downloads the thumbnail of a video message to a temporary file."""
    thumbnail_file = None
    if message.video.thumbs:
        thumbnail = message.video.thumbs[0] if message.video.thumbs else None
        unique_name = os.path.join(
            temp_path,
            "thumbnail",
            f"thumb-{int(time.time())}-{secrets.token_hex(8)}.jpg",
        )

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                thumbnail_file = await client.download_media(
                    thumbnail, file_name=unique_name
                )
                # 验证文件大小
                if os.path.getsize(thumbnail_file) == thumbnail.file_size:
                    break

                raise ValueError(
                    f"Thumbnail file size mismatch: {os.path.getsize(thumbnail_file)}"
                    f" vs expected {thumbnail.file_size}"
                )
            except Exception as e:
                if attempt == max_attempts:
                    logger.exception(f"Failed to download thumbnail: {e}")
                else:
                    await asyncio.sleep(2)

    return thumbnail_file
```

### 上传视频时使用完整属性

```python
# 关键：必须提供 thumb、width、height、duration
thumbnail_file = await download_thumbnail(client, temp_save_path, message)

await message.reply_video(
    video_file_path,
    caption=caption,
    thumb=thumbnail_file,              # 缩略图
    width=message.video.width,         # 视频宽度
    height=message.video.height,       # 视频高度
    duration=message.video.duration,   # 视频时长
    parse_mode=pyrogram.enums.ParseMode.HTML,
)
```

**注意事项:**
- 没有缩略图会导致视频显示为黑屏
- 缺少 width/height 会影响视频预览
- 上传后记得删除临时缩略图文件

---

## 4. 去除消息中的广告

通过分析消息实体(entities)来提取或过滤广告内容，同时保留原有格式。

### MessageProcessor 类

```python
import pyrogram

def get_utf16_length(text: str) -> int:
    """Get UTF-16 length of text (Telegram uses UTF-16 for entity offsets)"""
    return len(text.encode('utf-16-le')) // 2

class MessageProcessor:
    """Helper class for processing message captions and entities."""

    def __init__(self, raw_message, filter_str):
        self.raw_message = raw_message
        self.raw_caption = raw_message.caption
        self.filter_str = filter_str
        self.raw_filter_str = pyrogram.parser.utils.add_surrogates(filter_str)
        self.raw_caption_str = pyrogram.parser.utils.add_surrogates(raw_message.caption)
        self.idx = self.raw_caption_str.find(self.raw_filter_str)
        self.start_offset = self.idx
        self.end_offset = self.idx + get_utf16_length(filter_str)
        self.filtered_entities = []

    def process_entities(self):
        """Process and filter message entities."""
        for entity in self.raw_message.caption_entities:
            cur_start_offset = entity.offset
            cur_end_offset = entity.offset + entity.length

            # 检查实体是否在过滤范围内
            if (
                (cur_start_offset >= self.start_offset and cur_end_offset <= self.end_offset)
                or (cur_start_offset < self.start_offset and cur_end_offset > self.start_offset)
                or (cur_start_offset < self.end_offset and cur_end_offset > self.end_offset)
            ):
                self.filtered_entities.append(entity)

        self.filtered_entities.sort(key=lambda x: x.offset)

    def get_total_span(self):
        """Calculate the total span for text extraction."""
        if self.filtered_entities:
            first_entity = self.filtered_entities[0]
            last_entity = self.filtered_entities[-1]
            return (
                min(self.start_offset, first_entity.offset),
                max(self.end_offset, last_entity.offset + last_entity.length),
            )
        return (self.start_offset, self.end_offset)

    def extract_text(self, total_span):
        """Extract and process text with adjusted entity offsets."""
        text = self.raw_caption[total_span[0]:total_span[1]]
        for entity in self.filtered_entities:
            entity.offset -= total_span[0]
        return pyrogram.parser.Parser.unparse(text, self.filtered_entities, True)
```

### 处理广告替换

```python
async def proc_replace_advertisement(message_link: str, filter_str: str):
    """Process and replace advertisement content in a message."""
    chat_id, message_id, _ = await parse_link(client, message_link)
    raw_message = await client.get_messages(chat_id, message_id)

    processor = MessageProcessor(raw_message, filter_str)
    processor.process_entities()
    total_span = processor.get_total_span()
    return processor.extract_text(total_span)
```

**工作原理:**
1. 解析消息链接获取原始消息
2. 使用 filter_str 定位要保留的文本区域
3. 提取该区域内的实体(链接、加粗、斜体等)
4. 重新组装文本，保留格式但去除广告部分

**使用场景:**
- 转发消息时去除频道水印/广告
- 保留原始格式(链接、加粗、斜体等)
- 批量处理时添加到过滤列表

---

## 完整使用示例

```python
import pyrogram

# 1. 使用自定义超时的客户端
client = HookClient(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    start_timeout=120
)

async def main():
    await client.start()

    # 2. 解析消息链接
    link = "https://t.me/channel_name/123"
    chat_id, message_id, topic_id = await parse_link(client, link)

    # 3. 获取消息并下载视频
    message = await client.get_messages(chat_id, message_id)

    if message.video:
        # 下载缩略图避免黑屏
        thumbnail = await download_thumbnail(client, "/tmp", message)

        await client.send_video(
            chat_id=destination_chat,
            video=video_path,
            thumb=thumbnail,
            width=message.video.width,
            height=message.video.height,
            duration=message.video.duration,
        )

    # 4. 去除广告
    if message.caption:
        clean_caption = await proc_replace_advertisement(
            link,
            "想要的内容部分"
        )
        print(clean_caption)

    await client.stop()
```
