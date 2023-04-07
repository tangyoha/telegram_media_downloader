"""Bot for media downloader"""

import os
from typing import Callable, List

import pyrogram
from pyrogram import types
from pyrogram.handlers import MessageHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ruamel import yaml

from module.app import (
    Application,
    ChatDownloadConfig,
    DownloadStatus,
    DownloadTaskNode,
    Language,
)
from module.filter import Filter
from module.pyrogram_extension import report_bot_status
from utils.format import extract_info_from_link, replace_date_time, validate_title
from utils.meta_data import MetaData
from utils.updates import get_latest_release

# pylint: disable = C0301, R0902


class DownloadBot:
    """Download bot"""

    def __init__(self):
        self.bot = None
        self.client = None
        self.download_task: Callable = None
        self.download_chat_task: Callable = None
        self.app = None
        self.listen_forward_chat: dict = {}
        self.config: dict = {}
        self._yaml = yaml.YAML()
        self.config_path = os.path.join(os.path.abspath("."), "bot.yaml")
        self.download_command: dict = {}
        self.filter = Filter()

        meta = MetaData("2022/03/08 10:00:00", 0, "", 0, 0, 0, "", 0)
        self.filter.set_meta_data(meta)

        self.download_filter: List[str] = []

    def assign_config(self, _config: dict):
        """assign config from str.

        Parameters
        ----------
        _config: dict
            application config dict

        Returns
        -------
        bool
        """

        self.download_filter = _config.get("download_filter", self.download_filter)

        return True

    def update_config(self):
        """Update config from str."""
        self.config["download_filter"] = self.download_filter

        with open("d", "w", encoding="utf-8") as yaml_file:
            self._yaml.dump(self.config, yaml_file)

    async def set_bot_commands(self):
        """Set bot commands"""
        if self.app.language == Language.CN:
            commands = [
                types.BotCommand("help", "帮助"),
                types.BotCommand("download", "下载视频，使用方法直接输入/download查看"),
                types.BotCommand("forward", "转发视频，使用方法直接输入/forward查看"),
                types.BotCommand("listen_forward", "监控转发，使用方法直接输入/listen_forward查看"),
                types.BotCommand("add_filter", "添加下载过滤器"),
                types.BotCommand("set_language", "设置语言"),
            ]
        else:
            commands = [
                types.BotCommand("help", "Help"),
                types.BotCommand(
                    "download",
                    "To download the video, use the method to directly enter /download to view",
                ),
                types.BotCommand(
                    "forward",
                    "Forward video, use the method to directly enter /forward to view",
                ),
                types.BotCommand(
                    "listen_forward",
                    "Listen forward, use the method to directly enter /listen_forward to view",
                ),
                types.BotCommand(
                    "add_filter",
                    "Add download filter, use the method to directly enter /add_filter to view",
                ),
                types.BotCommand("set_language", "Set language"),
            ]

        await self.bot.set_bot_commands(commands)

    async def start(
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
            workdir=app.session_file_path,
            proxy=app.proxy,
        )

        self.bot.add_handler(
            MessageHandler(
                download_from_bot, filters=pyrogram.filters.command(["download"])
            )
        )
        self.bot.add_handler(
            MessageHandler(
                forward_messages, filters=pyrogram.filters.command(["forward"])
            )
        )
        self.bot.add_handler(
            MessageHandler(download_forward_media, filters=pyrogram.filters.media)
        )
        self.bot.add_handler(
            MessageHandler(
                download_from_link, filters=pyrogram.filters.regex(r"^https://t.me.*")
            )
        )
        self.bot.add_handler(
            MessageHandler(
                set_listen_forward_msg,
                filters=pyrogram.filters.command(["listen_forward"]),
            )
        )
        self.bot.add_handler(
            MessageHandler(help_command, filters=pyrogram.filters.command(["help"]))
        )
        self.bot.add_handler(
            MessageHandler(help_command, filters=pyrogram.filters.command(["start"]))
        )
        self.bot.add_handler(
            MessageHandler(
                set_language, filters=pyrogram.filters.command(["set_language"])
            )
        )
        self.bot.add_handler(
            MessageHandler(add_filter, filters=pyrogram.filters.command(["add_filter"]))
        )
        self.client = client

        self.client.add_handler(MessageHandler(listen_forward_msg))

        self.download_task = download_task
        self.download_chat_task = download_chat_task

        self.app = app

        # load config
        if os.path.exists(self.config_path):
            with open(self.config_path, encoding="utf-8") as f:
                config = self._yaml.load(f.read())
                if config:
                    self.config = config
                    self.assign_config(self.config)

        await self.bot.start()
        admin = await self.client.get_me()

        update_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Github",
                        url="https://github.com/tangyoha/telegram_media_downloader/releases",
                    ),
                    InlineKeyboardButton(
                        "Join us", url="https://t.me/TeegramMediaDownload"
                    ),
                ]
            ]
        )

        try:
            latest_release = get_latest_release()
            if latest_release:
                update_message = (
                    "**New version**:\n"
                    + f"**[{latest_release['name']}]({latest_release['html_url']})**"
                )
                await self.bot.send_message(
                    admin.id, update_message, reply_markup=update_keyboard
                )
        except Exception:
            pass

        await self.set_bot_commands()


_bot = DownloadBot()


async def start_download_bot(
    app: Application,
    client: pyrogram.Client,
    download_task: Callable,
    download_chat_task: Callable,
):
    """Start download bot"""
    await _bot.start(app, client, download_task, download_chat_task)


def stop_download_bot():
    """Stop download bot"""
    _bot.update_config()


async def help_command(client: pyrogram.Client, message: pyrogram.types.Message):
    """
    Sends a message with the available commands and their usage.

    Parameters:
        client (pyrogram.Client): The client instance.
        message (pyrogram.types.Message): The message object.

    Returns:
        None
    """

    if _bot.app.language is Language.CN:
        msg = (
            "可用命令:\n"
            "/help - 显示可用命令\n"
            # "/add_filter - 添加下载的过滤器\n"
            "/download - 下载消息\n"
            "/forward - 转发消息\n"
            "/listen_forward - 监听转发消息\n"
            "/set_language - 设置语言\n"
            "**注意**：1表示整个聊天的开始，"
            "0表示整个聊天的结束\n`[` `]` 表示可选项，非必填\n"
        )
    else:
        msg = (
            "Available commands:\n"
            "/help - Show available commands\n"
            # "/add_filter - Add download filter\n"
            "/download - Download messages\n"
            "/forward - Forward messages\n"
            "/listen_forward - Listen for forwarded messages\n"
            "/set_language - Set language\n"
            "Note: 1 means the start of the entire chat,"
            "0 means the end of the entire chat\n"
            "`[` `]` means optional, not required\n"
        )

    await client.send_message(message.chat.id, msg)


async def set_language(client: pyrogram.Client, message: pyrogram.types.Message):
    """
    Set the language of the bot.

    Parameters:
        client (pyrogram.Client): The pyrogram client.
        message (pyrogram.types.Message): The message containing the command.

    Returns:
        None
    """

    if len(message.text.split()) != 2:
        if _bot.app.language is Language.CN:
            await client.send_message(
                message.from_user.id, "无效的命令格式。请使用 /set_language cn/en"
            )
        else:
            await client.send_message(
                message.from_user.id,
                "Invalid command format. Please use /set_language cn/en",
            )
        return

    language = message.text.split()[1]

    if language.lower() == "cn":
        _bot.app.language = Language.CN
        await client.send_message(message.from_user.id, "语言设置为中文")
    elif language.lower() == "en":
        _bot.app.language = Language.EN
        await client.send_message(message.from_user.id, "Language set to English")
    else:
        if _bot.app.language is Language.CN:
            await client.send_message(message.from_user.id, "无效的语言选项。请使用 cn/en")
        else:
            await client.send_message(
                message.from_user.id, "Invalid language option. Please use cn/en"
            )

    await _bot.set_bot_commands()


async def add_filter(client: pyrogram.Client, message: pyrogram.types.Message):
    """
    Set the download filter of the bot.

    Parameters:
        client (pyrogram.Client): The pyrogram client.
        message (pyrogram.types.Message): The message containing the command.

    Returns:
        None
    """

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        if _bot.app.language is Language.CN:
            await client.send_message(
                message.from_user.id, "无效的命令格式。请使用 /add_filter 你的过滤规则"
            )
        else:
            await client.send_message(
                message.from_user.id,
                "Invalid command format. Please use /add_filter your filter",
            )
        return

    filter_str = replace_date_time(args[1])
    res, err = _bot.filter.check_filter(filter_str)
    if res:
        _bot.app.down = args[1]
        await client.send_message(
            message.from_user.id, f"Add download filter : {args[1]}"
        )
    else:
        if _bot.app.language is Language.CN:
            await client.send_message(message.from_user.id, f"{err}\n检验错误,请重新添加!")
        else:
            await client.send_message(message.from_user.id, f"{err}\nPlease try again!")
    return


async def download_forward_media(
    client: pyrogram.Client, message: pyrogram.types.Message
):
    """
    Downloads the media from a forwarded message.

    Parameters:
        client (pyrogram.Client): The client instance.
        message (pyrogram.types.Message): The message object.

    Returns:
        None
    """

    if _bot.app.language is Language.CN:
        msg = "1. 直接下载，直接转发消息给你的机器人\n\n"
    else:
        msg = "1. Direct download, directly forward the message to your robot\n\n"

    if message.media:
        if getattr(message, message.media.value):
            download_status, _ = await _bot.download_task(
                client,
                message,
                _bot.app.media_types,
                _bot.app.file_formats,
                client.name,
            )

            await _bot.bot.send_message(
                message.from_user.id,
                f"from `{message.from_user.first_name}`\n"
                f"* message id : `{message.id}`\n"
                f"* status: **{download_status.name}**",
            )

            return

    await client.send_message(
        message.from_user.id, msg, parse_mode=pyrogram.enums.ParseMode.HTML
    )


async def download_from_link(client: pyrogram.Client, message: pyrogram.types.Message):
    """
    Downloads a single message from a Telegram link.

    Parameters:
        client (pyrogram.Client): The pyrogram client.
        message (pyrogram.types.Message): The message containing the Telegram link.

    Returns:
        None
    """

    if not message.text or not message.text.startswith("https://t.me"):
        return
    if _bot.app.language is Language.CN:
        msg = "1. 直接下载单条消息\n<i>https://t.me/12000000/1</i>\n\n"
    else:
        msg = (
            "1. Directly download a single message\n"
            "<i>https://t.me/12000000/1</i>\n\n"
        )

    text = message.text.split()
    if len(text) != 1:
        await client.send_message(
            message.from_user.id, msg, parse_mode=pyrogram.enums.ParseMode.HTML
        )

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
            reply_message += f"download message id = {message_id} !\n......"
            last_reply_message = await client.send_message(
                message.from_user.id, reply_message
            )
            node = DownloadTaskNode(
                chat_id=entity.id,
                from_user_id=message.from_user.id,
                reply_message_id=last_reply_message.id,
                replay_message=reply_message,
            )

            await _bot.download_chat_task(
                _bot.client,
                chat_download_config,
                node,
                limit,
                _bot.bot,
            )
            await client.edit_message_text(
                message.from_user.id,
                last_reply_message.id,
                f"{node.reply_message}\n"
                f"total task is {chat_download_config.total_task}",
            )
            return

    await client.send_message(
        message.from_user.id, msg, parse_mode=pyrogram.enums.ParseMode.HTML
    )


# pylint: disable = R0912, R0915,R0914


async def download_from_bot(client: pyrogram.Client, message: pyrogram.types.Message):
    """Download from bot"""
    if _bot.app.language is Language.CN:
        msg = (
            "参数错误，请按照参考格式输入:\n\n"
            "1.下载普通群组所有消息\n"
            "<i>/download https://t.me/fkdhlg 1 0</i>\n\n"
            "私密群组(频道) 链接为随便复制一条群组消息链接\n\n"
            "2.下载从第N条消息开始的到第M条信息结束，"
            "M为0的时候表示到最后一条信息,过滤器为可选\n"
            "<i>/download https://t.me/12000000 N M [过滤器]</i>\n\n"
        )
    else:
        msg = (
            "Parameter error, please enter according to the reference format:\n\n"
            "1. Download all messages of common group\n"
            "<i>/download https://t.me/fkdhlg 1 0</i>\n\n"
            "The private group (channel) link is a random group message link\n\n"
            "2. The download starts from the N message to the end of the M message. "
            "When M is 0, it means the last message. The filter is optional\n"
            "<i>/download https://t.me/12000000 N M [filter]</i>\n\n"
        )

    args = message.text.split(maxsplit=4)
    if not message.text or len(args) < 4:
        await client.send_message(
            message.from_user.id, msg, parse_mode=pyrogram.enums.ParseMode.HTML
        )
        return

    url = args[1]
    try:
        offset_id = int(args[2])
        limit = int(args[3])
    except Exception:
        await client.send_message(
            message.from_user.id, msg, parse_mode=pyrogram.enums.ParseMode.HTML
        )
        return

    if limit:
        if limit < offset_id:
            raise ValueError("M > N")

        limit = limit - offset_id + 1

    download_filter = args[4] if len(args) > 4 else None

    if download_filter:
        download_filter = replace_date_time(download_filter)
        res, err = _bot.filter.check_filter(download_filter)
        if not res:
            await client.send_message(
                message.from_user.id, err, reply_to_message_id=message.id
            )
    try:
        chat_id, _ = extract_info_from_link(url)
        if chat_id:
            entity = await _bot.client.get_chat(chat_id)
        if entity:
            chat_title = entity.title
            reply_message = f"from {chat_title} "
            chat_download_config = ChatDownloadConfig()
            chat_download_config.last_read_message_id = offset_id
            chat_download_config.download_filter = download_filter
            reply_message += f"download message id = {offset_id} limit = {limit} !"
            last_reply_message = await client.send_message(
                message.from_user.id, reply_message, reply_to_message_id=message.id
            )
            node = DownloadTaskNode(
                chat_id=entity.id,
                from_user_id=message.from_user.id,
                reply_message_id=last_reply_message.id,
                replay_message=reply_message,
            )
            await _bot.download_chat_task(
                _bot.client,
                chat_download_config,
                node,
                limit,
                _bot.bot,
            )

            node.reply_message = (
                f"{node.reply_message}\n`total_task: {chat_download_config.total_task}`"
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


# pylint: disable = R0914
async def forward_messages(client: pyrogram.Client, message: pyrogram.types.Message):
    """
    Forwards messages from one chat to another.

    Parameters:
        client (pyrogram.Client): The pyrogram client.
        message (pyrogram.types.Message): The message containing the command.

    Returns:
        None
    """

    async def report_error(client: pyrogram.Client, message: pyrogram.types.Message):
        """Report error"""

        if _bot.app.language is Language.CN:
            await client.send_message(
                message.from_user.id,
                "无效的命令格式。请使用 "
                "/forward https://t.me/c/src_chat https://t.me/c/dst_chat "
                "1 400 `[`过滤器`]`\n",
            )
        else:
            await client.send_message(
                message.from_user.id,
                "Invalid command format. "
                "Please use /forward https://t.me/c/src_chat https://t.me/c/dst_chat "
                "1 400 `[`filter`]`",
            )
        return

    args = message.text.split(maxsplit=5)
    if len(args) < 5:
        await report_error(client, message)
        return

    src_chat_link = args[1]
    dst_chat_link = args[2]

    try:
        offset_id = int(args[3])
        limit = int(args[4])
    except Exception:
        await report_error(client, message)
        return

    if limit:
        if limit < offset_id:
            raise ValueError("limit id > offset id")

        limit = limit - offset_id + 1

    download_filter = args[5] if len(args) > 5 else None

    src_chat_id, _ = extract_info_from_link(src_chat_link)
    dst_chat_id, _ = extract_info_from_link(dst_chat_link)

    if not src_chat_id or not dst_chat_id:
        if _bot.app.language is Language.CN:
            await client.send_message(
                message.from_user.id, "无效的聊天链接", reply_to_message_id=message.id
            )
        else:
            await client.send_message(
                message.from_user.id,
                "Invalid chat link",
                reply_to_message_id=message.id,
            )
        return

    try:
        src_chat = await _bot.client.get_chat(src_chat_id)
        dst_chat = await _bot.client.get_chat(dst_chat_id)
    except Exception:
        if _bot.app.language is Language.CN:
            await client.send_message(
                message.from_user.id, "无效的聊天链接", reply_to_message_id=message.id
            )
        else:
            await client.send_message(
                message.from_user.id,
                "Invalid chat link",
                reply_to_message_id=message.id,
            )
        return

    me = await client.get_me()
    if dst_chat.id == me.id:
        if _bot.app.language is Language.CN:
            # TODO: when bot receive message judge if download
            await client.send_message(
                message.from_user.id,
                "不能转发给该机器人，会导致无限循环",
                reply_to_message_id=message.id,
            )
        else:
            await client.send_message(
                message.from_user.id,
                "Can not forward to self",
                reply_to_message_id=message.id,
            )
        return

    if download_filter:
        download_filter = replace_date_time(download_filter)
        res, err = _bot.filter.check_filter(download_filter)
        if not res:
            await client.send_message(
                message.from_user.id, err, reply_to_message_id=message.id
            )

    last_reply_message = await client.send_message(
        message.from_user.id,
        "Forwarding message, please wait...",
        reply_to_message_id=message.id,
    )

    node = DownloadTaskNode(
        chat_id=src_chat_id,
        from_user_id=message.from_user.id,
        upload_telegram_chat_id=dst_chat_id,
        reply_message_id=last_reply_message.id,
        replay_message=last_reply_message.text,
    )

    if not src_chat.has_protected_content:
        last_read_message_id = offset_id
        try:
            async for item in _bot.client.get_chat_history(
                src_chat.id,
                limit=limit,
                offset_id=offset_id,
                reverse=True,
            ):
                # TODO if not exist filter forward 10 per
                # await _bot.client.forward_messages(dst_chat_id, src_chat_id, list(range(i, i + 10)))
                if download_filter:
                    meta_data = MetaData()
                    caption = item.caption
                    if caption:
                        caption = validate_title(caption)
                        _bot.app.set_caption_name(
                            src_chat_id, item.media_group_id, caption
                        )
                    else:
                        caption = _bot.app.get_caption_name(
                            src_chat_id, item.media_group_id
                        )

                    meta_data.get_meta_data(item)
                    if not _bot.filter.exec(download_filter):
                        continue
                status = DownloadStatus.SuccessDownload
                try:
                    await _bot.client.forward_messages(
                        dst_chat.id, src_chat.id, item.id
                    )
                except Exception:
                    status = DownloadStatus.FailedDownload

                await report_bot_status(client, node, item, status)
                last_read_message_id = item.id

        except Exception as e:
            if _bot.app.language is Language.CN:
                await client.edit_message_text(
                    message.from_user.id,
                    last_reply_message.id,
                    f"转发消息 {last_read_message_id} - {offset_id + limit} 失败 : {e}",
                )
            else:
                await client.edit_message_text(
                    message.from_user.id,
                    last_reply_message.id,
                    f"Error forwarding message {last_read_message_id} - {offset_id + limit} {e}",
                )

    else:
        chat_download_config = ChatDownloadConfig()
        chat_download_config.last_read_message_id = offset_id
        chat_download_config.download_filter = download_filter

        await _bot.download_chat_task(
            _bot.client,
            chat_download_config,
            node,
            limit,
            _bot.bot,
        )

        node.reply_message = (
            f"{node.reply_message}\n`total_task: {chat_download_config.total_task}`"
        )


async def set_listen_forward_msg(
    client: pyrogram.Client, message: pyrogram.types.Message
):
    """
    Set the chat to listen for forwarded messages.

    Args:
        client (pyrogram.Client): The pyrogram client.
        message (pyrogram.types.Message): The message sent by the user.

    Returns:
        None
    """
    args = message.text.split(maxsplit=3)

    if len(args) < 3:
        if _bot.app.language is Language.CN:
            await client.send_message(
                message.from_user.id,
                "无效的命令格式。请使用 /listen_forward "
                "https://t.me/c/src_chat https://t.me/c/dst_chat [过滤器]",
            )
        else:
            await client.send_message(
                message.from_user.id,
                "Invalid command format. Please use /listen_forward "
                "https://t.me/c/src_chat https://t.me/c/dst_chat [filter]\n",
            )
        return

    src_chat_link = args[1]
    dst_chat_link = args[2]

    src_chat_id, _ = extract_info_from_link(src_chat_link)
    dst_chat_id, _ = extract_info_from_link(dst_chat_link)

    try:
        src_chat = await _bot.client.get_chat(src_chat_id)
        dst_chat = await _bot.client.get_chat(dst_chat_id)
    except Exception:
        if _bot.app.language is Language.CN:
            await client.send_message(
                message.from_user.id, "无效的聊天链接", reply_to_message_id=message.id
            )
        else:
            await client.send_message(
                message.from_user.id,
                "Invalid chat link",
                reply_to_message_id=message.id,
            )
        return

    _bot.listen_forward_chat[src_chat.id] = (
        dst_chat.id,
        replace_date_time(args[3]) if len(args) > 3 else None,
    )


async def listen_forward_msg(client: pyrogram.Client, message: pyrogram.types.Message):
    """
    Forwards messages from a chat to another chat if the message does not contain protected content.
    If the message contains protected content, it will be downloaded and forwarded to the other chat.

    Parameters:
        client (pyrogram.Client): The pyrogram client.
        message (pyrogram.types.Message): The message to be forwarded.
    """

    if message.chat and message.chat.id in _bot.listen_forward_chat:
        chat_id, download_filter = _bot.listen_forward_chat[message.chat.id]

        last_reply_message = await client.send_message(
            message.from_user.id, "Forwarding message, please wait..."
        )
        if not message.chat.has_protected_content:
            await _bot.client.forward_messages(
                chat_id=chat_id, from_chat_id=message.chat.id, message_ids=message.id
            )
        else:
            chat_download_config = ChatDownloadConfig()
            chat_download_config.last_read_message_id = message.id
            chat_download_config.download_filter = download_filter
            node = DownloadTaskNode(
                chat_id=message.chat.id,
                from_user_id=message.from_user.id,
                upload_telegram_chat_id=chat_id,
                reply_message_id=last_reply_message.id,
                replay_message=last_reply_message.text,
            )
            await _bot.download_chat_task(
                _bot.client,
                chat_download_config,
                node,
                1,
                _bot.bot,
            )
