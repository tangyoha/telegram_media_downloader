"""Bot for media downloader"""

from typing import Callable

import pyrogram
from pyrogram.handlers import MessageHandler

from module.app import Application, ChatDownloadConfig, Language
from utils.format import extract_info_from_link


class DownloadBot:
    """Download bot"""

    def __init__(self):
        self.bot = None
        self.client = None
        self.download_task: Callable = None
        self.download_chat_task: Callable = None
        self.app = None

    def start(
        self,
        app: Application,
        client: pyrogram.Client,
        download_task: Callable,
        download_chat_task: Callable,
    ):
        """Start bot"""
        self.bot = pyrogram.Client(
            app.application_name + "_bot",
            api_hash=app.api_hash,
            api_id=app.api_id,
            bot_token=app.bot_token,
            proxy=app.proxy,
        )

        self.bot.add_handler(MessageHandler(download_from_bot))

        self.client = client

        self.download_task = download_task
        self.download_chat_task = download_chat_task

        self.app = app

        self.bot.start()


_bot = DownloadBot()


def start_download_bot(
    app: Application,
    client: pyrogram.Client,
    download_task: Callable,
    download_chat_task: Callable,
):
    """Start download bot"""
    _bot.start(app, client, download_task, download_chat_task)


# pylint: disable = R0912, R0915
async def download_from_bot(client: pyrogram.Client, message: pyrogram.types.Message):
    """Download from bot"""
    if _bot.app.language is Language.CN:
        msg = (
            "参数错误，请按照参考格式输入:\n\n"
            "1.下载普通群组所有消息\n"
            "<i>/download https://t.me/fkdhlg</i>\n\n"
            "私密群组(频道) 链接为随便复制一条群组消息链接\n\n"
            "2.下载从第0条消息开始的所有消息\n"
            "<i>/download https://t.me/12000000</i>\n\n"
            "3.下载从第2条消息开始,100结束\n"
            "<i>/download https://t.me/12000000 2</i>\n\n"
            "4.下载从第2条消息开始,100结束\n"
            "<i>/download https://t.me/12000000 2 100</i>\n\n"
            "5. 直接下载，直接转发消息给你的机器人\n\n"
            "6. 直接下载单条消息\n"
            "<i>https://t.me/12000000/1</i>\n\n"
        )
    else:
        msg = (
            "parameter error, please enter according to the reference format:\n\n"
            "1. Download all messages of ordinary groups\n"
            "<i>/download https://t.me/fkdhlg</i>\n\n"
            "The private group (channel) link is just copy a group message link\n\n"
            "2. Download all messages starting from message 0\n"
            "<i>/download https://t.me/12000000</i>\n\n"
            "3. The download starts from the 2nd message and ends at 100\n"
            "<i>/download https://t.me/12000000 2</i>\n\n"
            "4. The download starts from the 2nd message and ends at 100\n"
            "<i>/download https://t.me/12000000 2 100</i>\n\n"
            "5. Direct download, direct message to your robot\n\n"
            "6. Directly download a single message\n"
            "<i>https://t.me/12000000/1</i>\n\n"
        )

    if message.media:
        media = getattr(message, message.media.value)
        if media:
            await _bot.download_task(
                client,
                message,
                _bot.app.media_types,
                _bot.app.file_formats,
                client.name,
            )
            return

    if not message.text:
        await client.send_message(
            message.from_user.id, msg, parse_mode=pyrogram.enums.ParseMode.HTML
        )
        return

    text = message.text.split()

    if len(text) == 1:
        chat_id, message_id = extract_info_from_link(text[0])
        entity = None
        if chat_id:
            entity = await _bot.client.get_chat(chat_id)

        if entity:
            chat_title = entity.title

            reply_message = f"from {chat_title} "

            chat_download_config = ChatDownloadConfig()

            if message_id:
                # download signal message
                limit = 1
                chat_download_config.last_read_message_id = message_id
                reply_message += f"download message id = {message_id} !"

                await client.send_message(message.from_user.id, reply_message)
                await _bot.download_chat_task(
                    _bot.client,
                    entity.id,
                    chat_download_config,
                    limit,
                    _bot.bot,
                    message.from_user.id,
                )
                return

        await client.send_message(
            message.from_user.id, msg, parse_mode=pyrogram.enums.ParseMode.HTML
        )
        return

    if len(text) >= 2:
        url = text[1]
        offset_id = 0
        limit = 0
        if len(text) >= 3:
            offset_id = int(text[2])
        if len(text) >= 4:
            if int(text[3]) < offset_id:
                raise ValueError("limit id > offset id")
            limit = int(text[3]) - offset_id + 1

        try:
            chat_id, message_id = extract_info_from_link(url)

            if chat_id:
                entity = await _bot.client.get_chat(chat_id)

            if entity:
                chat_title = entity.title

                reply_message = f"from {chat_title} "

                chat_download_config = ChatDownloadConfig()

                chat_download_config.last_read_message_id = offset_id
                reply_message += f"download message id = {offset_id} limit = {limit} !"

                await client.send_message(message.from_user.id, reply_message)

                await _bot.download_chat_task(
                    _bot.client,
                    entity.id,
                    chat_download_config,
                    limit,
                    _bot.bot,
                    message.from_user.id,
                )
        except Exception as e:
            if _bot.app.language is Language.CN:
                await client.send_message(
                    message.from_user.id,
                    "chat输入错误，请输入频道或群组的链接\n\n" f"错误类型：{e.__class__}" f"异常消息：{e}",
                )
            else:
                await client.send_message(
                    message.from_user.id,
                    "chat input error, please enter the channel or group link\n\n"
                    f"Error type: {e.__class__}"
                    f"Exception message: {e}",
                )
            return
    else:
        await client.send_message(
            message.from_user.id, msg, parse_mode=pyrogram.enums.ParseMode.HTML
        )
        return
