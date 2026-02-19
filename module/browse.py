"""Browse-and-select media feature for telegram_media_downloader."""

import asyncio
import io
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import pyrogram
from loguru import logger
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

from module.app import TaskNode
from module.language import _t

try:
    from PIL import Image

    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False
    logger.warning("browse: Pillow not installed; thumbnails will not be resized")


# Module-level state: (bot_chat_id, req_id) → BrowseRequest
_browse_reqs: Dict[Tuple[int, str], "BrowseRequest"] = {}


@dataclass
class BrowseItem:
    msg_id: int
    kind: str  # "photo" | "video" | "video_note"
    date_utc: datetime
    sender: str
    selected: bool = False
    downloaded: bool = False


@dataclass
class BrowseRequest:
    source_chat_id: int  # entity/channel being browsed (for TaskNode.chat_id)
    created_ts: float
    target: str
    minutes: int
    items: Dict[int, BrowseItem]
    msg_map: Dict[int, object]  # msg_id → pyrogram Message
    control_msg_id: Optional[int] = None
    thumb_msg_ids: List[int] = field(default_factory=list)
    batch_header_msg_id: Optional[int] = None


def _get_bot():
    """Lazy import to avoid circular dependency with bot.py."""
    from module.bot import _bot  # noqa: PLC0415

    return _bot


def _get_media_kind(msg) -> str:
    """Classify pyrogram message media into kind string."""
    if getattr(msg, "photo", None):
        return "photo"
    if getattr(msg, "video_note", None):
        return "video_note"
    if getattr(msg, "video", None):
        return "video"
    return ""


def _get_sender_label(msg) -> str:
    """Return a human-readable sender string."""
    if getattr(msg, "from_user", None):
        u = msg.from_user.username
        if u:
            return f"@{u}"
        name = (msg.from_user.first_name or "").strip()
        if name:
            return name
        return str(msg.from_user.id)
    if getattr(msg, "sender_chat", None):
        return (
            msg.sender_chat.username or msg.sender_chat.title or str(msg.sender_chat.id)
        )
    return "unknown"


def _normalize_target(raw: str) -> str:
    """Normalize target to '@username' or numeric id string."""
    s = (raw or "").strip()
    m = re.match(
        r"^(?:https?://)?(?:t\.me|telegram\.me)/([^/?#]+)", s, flags=re.IGNORECASE
    )
    if m:
        s = m.group(1)
    s = s.lstrip("@").strip()
    if re.fullmatch(r"-?\d+", s):
        return s
    return "@" + s


def _parse_browse_args(text: str) -> Optional[Tuple[str, int]]:
    """Parse 'target N' argument string. Returns (target, minutes) or None."""
    text = (text or "").strip()
    m = re.match(
        r"^(\S+)\s+(\d+)\s*(?:m|min|mins|minutes)?$", text, flags=re.IGNORECASE
    )
    if not m:
        return None
    target = _normalize_target(m.group(1))
    minutes = int(m.group(2))
    return target, minutes


def _resize_jpeg(data: bytes, max_side: int = 512) -> bytes:
    """Resize image bytes and return JPEG bytes. Returns original if PIL unavailable."""
    if not _PIL_AVAILABLE:
        return data
    try:
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
            im.thumbnail((max_side, max_side))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=85, optimize=True)
            return buf.getvalue()
    except Exception as e:
        logger.warning(f"browse: _resize_jpeg failed: {e}")
        return data


def _build_control_keyboard(
    req_id: str, items: Dict[int, BrowseItem], per_row: int = 3
) -> InlineKeyboardMarkup:
    """Build inline keyboard for the browse control panel."""
    sorted_ids = sorted(items.keys())  # ascending msg_id = oldest first

    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for mid in sorted_ids:
        it = items[mid]
        if it.downloaded:
            label = f"📥#{mid}"
        elif it.selected:
            label = f"✅#{mid}"
        else:
            label = f"⬜#{mid}"
        row.append(
            InlineKeyboardButton(label, callback_data=f"tgdl|{req_id}|{mid}|toggle")
        )
        if len(row) >= per_row:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                f"📥 {_t('Download selected')}", callback_data=f"tgdl|{req_id}|0|done"
            ),
            InlineKeyboardButton(f"❌ {_t('Cancel')}", callback_data=f"tgdl|{req_id}|0|cancel"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def _ensure_thumb_dir() -> str:
    """Return (and create if needed) the browse thumbnail temp directory."""
    _bot = _get_bot()
    thumb_dir = os.path.join(_bot.app.temp_save_path, "browse_thumbs")
    os.makedirs(thumb_dir, exist_ok=True)
    return thumb_dir


async def _photo_thumb_bytes(client: pyrogram.Client, msg) -> Optional[bytes]:
    """Download a photo message thumbnail and return resized JPEG bytes."""
    try:
        photo = getattr(msg, "photo", None)
        if not photo:
            return None

        thumb_dir = _ensure_thumb_dir()
        tmp_path = os.path.join(thumb_dir, f"browse_photo_{secrets.token_hex(8)}.jpg")

        # Prefer a thumbnail PhotoSize; fall back to full photo
        thumb_obj = None
        thumbs = getattr(photo, "thumbs", None)
        if thumbs:
            # Iterate from largest to smallest to get a readable preview
            for t in reversed(thumbs):
                if getattr(t, "file_size", None):
                    thumb_obj = t
                    break
            if thumb_obj is None:
                thumb_obj = thumbs[-1]

        target = thumb_obj if thumb_obj else photo
        downloaded = await client.download_media(target, file_name=tmp_path)

        if not downloaded or not os.path.exists(downloaded):
            return None

        with open(downloaded, "rb") as f:
            data = f.read()

        try:
            os.unlink(downloaded)
        except Exception:
            pass

        return _resize_jpeg(data) if data else None
    except Exception as e:
        logger.warning(f"browse: _photo_thumb_bytes failed: {e}")
        return None


async def _video_thumb_bytes(client: pyrogram.Client, msg) -> Optional[bytes]:
    """Download a video/video_note thumbnail and return resized JPEG bytes."""
    try:
        media = getattr(msg, "video", None) or getattr(msg, "video_note", None)
        if not media:
            return None

        thumbs = getattr(media, "thumbs", None)
        if not thumbs:
            return None

        thumb_dir = _ensure_thumb_dir()
        tmp_path = os.path.join(thumb_dir, f"browse_video_{secrets.token_hex(8)}.jpg")

        downloaded = await client.download_media(thumbs[0], file_name=tmp_path)

        if not downloaded or not os.path.exists(downloaded):
            return None

        with open(downloaded, "rb") as f:
            data = f.read()

        try:
            os.unlink(downloaded)
        except Exception:
            pass

        return _resize_jpeg(data) if data else None
    except Exception as e:
        logger.warning(f"browse: _video_thumb_bytes failed: {e}")
        return None


async def browse_command(
    client: pyrogram.Client,
    message: pyrogram.types.Message,
    max_history_minute: int = 720,
    chat_history_limit: int = 5000,
    max_msg_return: int = 100,
):
    """Handle /browse @target N — browse and select media from a chat."""
    _bot = _get_bot()

    usage = (
        f"{_t('Usage')}: /browse @target N\n"
        f"{_t('Example')}: /browse @somechannel 10\n"
        f"{_t('Fetches photos/videos from the last N minutes')} (1–{max_history_minute})."
    )

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await client.send_message(message.chat.id, usage)
        return

    parsed = _parse_browse_args(f"{args[1]} {args[2]}")
    if not parsed:
        await client.send_message(message.chat.id, usage)
        return

    target, minutes = parsed
    minutes = max(1, min(minutes, max_history_minute))
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    try:
        entity = await _bot.client.get_chat(target)
    except Exception as e:
        await client.send_message(message.chat.id, f"{_t('Target not found')}: {target}\n{e}")
        return

    # Fetch recent messages via user client (newest → oldest)
    items: Dict[int, BrowseItem] = {}
    msg_map: Dict[int, object] = {}
    try:
        async for msg in _bot.client.get_chat_history(
            entity.id, limit=chat_history_limit
        ):
            if not msg.date:
                continue
            msg_dt = msg.date
            # Pyrogram 2.1.22 returns datetime.fromtimestamp() — naive local time.
            # astimezone() treats naive datetimes as local and converts to true UTC.
            # Also handles any already-aware (non-UTC) datetime correctly.
            msg_dt = msg_dt.astimezone(timezone.utc)
            if msg_dt < since:
                break
            kind = _get_media_kind(msg)
            if not kind:
                continue
            items[msg.id] = BrowseItem(
                msg_id=msg.id,
                kind=kind,
                date_utc=msg_dt,
                sender=_get_sender_label(msg),
            )
            msg_map[msg.id] = msg
            if len(items) >= max_msg_return:
                break
    except Exception as e:
        await client.send_message(message.chat.id, f"{_t('Error fetching messages')}: {e}")
        return

    if not items:
        await client.send_message(
            message.chat.id,
            f"{_t('No photos/videos found in')} {target} {_t('in the past')} {minutes} {_t('minutes')}.",
        )
        return

    bot_chat_id = message.chat.id
    limit_hit = len(items) >= max_msg_return
    summary = f"{_t('Found')} {len(items)} {_t('media items')} ({target}, {_t('in the past')} {minutes} {_t('minutes')})."
    if limit_hit:
        summary += f" ⚠️ {_t('Limit of')} {max_msg_return} {_t('items reached — older items in the window were not fetched.')}"
    await client.send_message(bot_chat_id, summary)

    # Split into batches of 10, ordered oldest → newest (msg_id is monotonically increasing)
    sorted_ids = sorted(items.keys())
    batches = [sorted_ids[i : i + 10] for i in range(0, len(sorted_ids), 10)]

    for bi, batch_ids in enumerate(batches, start=1):
        batch_req_id = f"{uuid.uuid4().hex[:6]}b{bi}"
        batch_items = {mid: items[mid] for mid in batch_ids}
        batch_msg_map = {mid: msg_map[mid] for mid in batch_ids}

        req = BrowseRequest(
            source_chat_id=entity.id,
            created_ts=time.time(),
            target=target,
            minutes=minutes,
            items=batch_items,
            msg_map=batch_msg_map,
        )
        _browse_reqs[(bot_chat_id, batch_req_id)] = req

        batch_header_msg = await client.send_message(
            bot_chat_id,
            f"📦 {_t('Batch')} {bi}/{len(batches)}: {len(batch_ids)} {_t('items')}",
        )
        req.batch_header_msg_id = batch_header_msg.id

        # Download thumbnails in parallel, oldest → newest
        thumb_dir = _ensure_thumb_dir()
        sorted_batch_ids = sorted(batch_ids)

        async def _fetch_thumb(mid: int):
            msg_obj = batch_msg_map[mid]
            it = batch_items[mid]
            if it.kind == "photo":
                return mid, await _photo_thumb_bytes(_bot.client, msg_obj)
            if it.kind in {"video", "video_note"}:
                return mid, await _video_thumb_bytes(_bot.client, msg_obj)
            return mid, None

        results = await asyncio.gather(*(_fetch_thumb(mid) for mid in sorted_batch_ids))

        thumb_paths: List[str] = []
        for mid, thumb_data in results:
            if not thumb_data:
                continue
            tmp_path = os.path.join(
                thumb_dir, f"send_thumb_{mid}_{secrets.token_hex(4)}.jpg"
            )
            with open(tmp_path, "wb") as f:
                f.write(thumb_data)
            thumb_paths.append(tmp_path)

        # Send thumbnails to user and record message IDs for later cleanup
        if len(thumb_paths) == 1:
            sent = await client.send_photo(bot_chat_id, thumb_paths[0])
            req.thumb_msg_ids.append(sent.id)
        elif len(thumb_paths) >= 2:
            media_group = [InputMediaPhoto(p) for p in thumb_paths]
            sent_msgs = await client.send_media_group(bot_chat_id, media_group)
            req.thumb_msg_ids.extend(m.id for m in sent_msgs)
        else:
            await client.send_message(
                bot_chat_id,
                _t("(No thumbnails available for this batch; you can still select items via the control panel.)"),
            )

        # Clean up temp thumb files
        for p in thumb_paths:
            try:
                os.unlink(p)
            except Exception:
                pass

        # Send control panel
        control_msg = await client.send_message(
            bot_chat_id,
            f"{_t('Control panel')} ({_t('Batch')} {bi}/{len(batches)}): {_t('tap items to select (✅ = selected), then press Download.')}",
            reply_markup=_build_control_keyboard(batch_req_id, batch_items),
        )
        req.control_msg_id = control_msg.id


async def _cleanup_browse_req(bot_chat_id: int, req: "BrowseRequest") -> None:
    """Delete thumbnail and control-panel messages for a finished BrowseRequest."""
    ids_to_delete: List[int] = list(req.thumb_msg_ids)
    if req.batch_header_msg_id:
        ids_to_delete.append(req.batch_header_msg_id)
    if req.control_msg_id:
        ids_to_delete.append(req.control_msg_id)
    if not ids_to_delete:
        return
    try:
        await _get_bot().bot.delete_messages(bot_chat_id, ids_to_delete)
    except Exception as e:
        logger.warning(f"browse: failed to delete messages on cleanup: {e}")


async def handle_browse_callback(
    client: pyrogram.Client, query: pyrogram.types.CallbackQuery
):
    """Handle tgdl| callback queries from browse control panels."""
    _bot = _get_bot()

    try:
        _, req_id, msg_id_s, action = query.data.split("|")
        msg_id = int(msg_id_s)
    except Exception:
        await query.answer(_t("Bad callback data"), show_alert=True)
        return

    bot_chat_id = query.message.chat.id
    key = (bot_chat_id, req_id)
    req = _browse_reqs.get(key)

    if not req:
        await query.answer(
            _t("This selection has expired. Please send /browse again."), show_alert=True
        )
        return

    if time.time() - req.created_ts > 1800:
        _browse_reqs.pop(key, None)
        await query.answer(_t("Expired. Please send /browse again."), show_alert=True)
        return

    if action == "toggle":
        it = req.items.get(msg_id)
        if not it:
            await query.answer(_t("Item not found"), show_alert=True)
            return
        if it.downloaded:
            await query.answer(_t("Already downloaded."), show_alert=True)
            return
        it.selected = not it.selected
        await query.answer("OK")
        if req.control_msg_id:
            try:
                await client.edit_message_reply_markup(
                    bot_chat_id,
                    req.control_msg_id,
                    reply_markup=_build_control_keyboard(req_id, req.items),
                )
            except Exception as e:
                logger.warning(f"browse: failed to update control keyboard: {e}")
        return

    if action == "cancel":
        _browse_reqs.pop(key, None)
        await query.answer(_t("Cancelled"))
        await _cleanup_browse_req(bot_chat_id, req)
        await client.send_message(bot_chat_id, f"{_t('Cancelled')}.")
        return

    if action == "done":
        selected_ids = [mid for mid, it in req.items.items() if it.selected]
        if not selected_ids:
            await query.answer(_t("You haven't selected any items yet."), show_alert=True)
            return

        await query.answer(_t("Starting download..."))

        status_msg = await client.send_message(
            bot_chat_id,
            f"{_t('Downloading')} {len(selected_ids)} {_t('selected items')}...",
        )

        node = TaskNode(
            chat_id=req.source_chat_id,
            from_user_id=query.from_user.id,
            reply_message_id=status_msg.id,
            replay_message=f"{_t('Downloading')} {len(selected_ids)} {_t('selected items')}",
            limit=len(selected_ids),
            bot=_bot.bot,
            task_id=_bot.gen_task_id(),
        )
        node.client = _bot.client

        _bot.add_task_node(node)

        for mid in selected_ids:
            await _bot.add_download_task(req.msg_map[mid], node)
            req.items[mid].selected = False
            req.items[mid].downloaded = True

        node.is_running = True

        # Update keyboard to reflect downloaded state; keep session alive for further picks
        if req.control_msg_id:
            try:
                await client.edit_message_reply_markup(
                    bot_chat_id,
                    req.control_msg_id,
                    reply_markup=_build_control_keyboard(req_id, req.items),
                )
            except Exception as e:
                logger.warning(f"browse: failed to update control keyboard after download: {e}")


async def gc_browse_reqs_loop(interval_sec: int = 60, ttl_sec: int = 1800):
    """Background task: garbage-collect expired BrowseRequests."""
    while True:
        now = time.time()
        expired = [
            k for k, req in list(_browse_reqs.items()) if now - req.created_ts > ttl_sec
        ]
        for k in expired:
            req = _browse_reqs.pop(k, None)
            if req:
                bot_chat_id = k[0]
                await _cleanup_browse_req(bot_chat_id, req)
        await asyncio.sleep(interval_sec)
