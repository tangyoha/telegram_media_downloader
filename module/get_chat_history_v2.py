"""Rewrite pyrogram.get_chat_history"""

from datetime import datetime
from typing import AsyncGenerator, Optional, Union

import pyrogram
from pyrogram import raw, types, utils


async def get_chunk_v2(
    *,
    client: pyrogram.Client,
    chat_id: Union[int, str],
    limit: int = 0,
    offset: int = 0,
    from_message_id: int = 0,
    from_date: datetime = utils.zero_datetime(),
    reverse: bool = False
):
    """get chunk"""
    from_message_id = from_message_id or (1 if reverse else 0)

    messages = await utils.parse_messages(
        client,
        await client.invoke(
            raw.functions.messages.GetHistory(
                peer=await client.resolve_peer(chat_id),
                offset_id=from_message_id,
                offset_date=utils.datetime_to_timestamp(from_date),
                add_offset=offset * (-1 if reverse else 1) - (limit if reverse else 0),
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0,
            ),
            sleep_threshold=60,
        ),
        replies=0,
    )

    if reverse:
        messages.reverse()

    return messages


# pylint disable=C0301


async def get_chat_history_v2(
    self: pyrogram.Client,
    chat_id: Union[int, str],
    limit: int = 0,
    offset: int = 0,
    offset_id: int = 0,
    offset_date: datetime = utils.zero_datetime(),
    reverse: bool = False,
) -> Optional[AsyncGenerator["types.Message", None]]:
    """Get messages from a chat history.

    The messages are returned in reverse chronological order.

    .. include:: /_includes/usable-by/users.rst

    Parameters:
        chat_id (``int`` | ``str``):
            Unique identifier (int) or username (str) of the target chat.
            For your personal cloud (Saved Messages) you can simply use "me" or "self".
            For a contact that exists in your Telegram address book you can use his phone number (str).

        limit (``int``, *optional*):
            Limits the number of messages to be retrieved.
            By default, no limit is applied and all messages are returned.

        offset (``int``, *optional*):
            Sequential number of the first message to be returned..
            Negative values are also accepted and become useful in case you set offset_id or offset_date.

        offset_id (``int``, *optional*):
            Identifier of the first message to be returned.

        offset_date (:py:obj:`~datetime.datetime`, *optional*):
            Pass a date as offset to retrieve only older messages starting from that date.

        reverse (``bool``, *optional*):
            Pass True to retrieve the messages in reversed order (from older to most recent).

    Returns:
        ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.

    Example:
        .. code-block:: python

            async for message in app.get_chat_history(chat_id):
                print(message.text)
    """
    current = 0
    total = limit or (1 << 31) - 1
    limit = min(100, total)

    while True:
        messages = await get_chunk_v2(
            client=self,
            chat_id=chat_id,
            limit=limit,
            offset=offset,
            from_message_id=offset_id,
            from_date=offset_date,
            reverse=reverse,
        )

        if not messages:
            return

        offset_id = messages[-1].id + (1 if reverse else 0)

        for message in messages:
            yield message

            current += 1

            if current >= total:
                return
