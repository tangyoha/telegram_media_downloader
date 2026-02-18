"""Browse-and-select media feature for telegram_media_downloader."""

import asyncio
import io
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import pyrogram
from loguru import logger
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

from module.app import TaskNode

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


@dataclass
class BrowseRequest:
    source_chat_id: int  # entity/channel being browsed (for TaskNode.chat_id)
    created_ts: float
    target: str
    minutes: int
    items: Dict[int, BrowseItem]
    msg_map: Dict[int, object]  # msg_id → pyrogram Message
    control_msg_id: Optional[int] = None


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
        return msg.sender_chat.username or msg.sender_chat.title or str(msg.sender_chat.id)
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
        label = f"✅#{mid}" if it.selected else f"⬜#{mid}"
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
                "📥 Download selected", callback_data=f"tgdl|{req_id}|0|done"
            ),
            InlineKeyboardButton(
                "❌ Cancel", callback_data=f"tgdl|{req_id}|0|cancel"
            ),
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
        tmp_path = os.path.join(
            thumb_dir, f"browse_photo_{secrets.token_hex(8)}.jpg"
        )

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
        tmp_path = os.path.join(
            thumb_dir, f"browse_video_{secrets.token_hex(8)}.jpg"
        )

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


async def browse_command(client: pyrogram.Client, message: pyrogram.types.Message):
    """Handle /browse @target N — browse and select media from a chat."""
    _bot = _get_bot()

    usage = (
        "Usage: /browse @target N\n"
        "Example: /browse @somechannel 10\n"
        "Fetches photos/videos from the last N minutes (1–720)."
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
    minutes = max(1, min(minutes, 720))
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    try:
        entity = await _bot.client.get_chat(target)
    except Exception as e:
        await client.send_message(message.chat.id, f"Target not found: {target}\n{e}")
        return

    # Fetch recent messages via user client (newest → oldest)
    items: Dict[int, BrowseItem] = {}
    msg_map: Dict[int, object] = {}
    try:
        async for msg in _bot.client.get_chat_history(entity.id, limit=200):
            if not msg.date:
                continue
            msg_dt = msg.date
            if msg_dt.tzinfo is None:
                msg_dt = msg_dt.replace(tzinfo=timezone.utc)
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
            if len(items) >= 20:
                break
    except Exception as e:
        await client.send_message(message.chat.id, f"Error fetching messages: {e}")
        return

    if not items:
        await client.send_message(
            message.chat.id,
            f"No photos/videos found in {target} in the past {minutes} minutes.",
        )
        return

    bot_chat_id = message.chat.id
    await client.send_message(
        bot_chat_id,
        f"Found {len(items)} media items ({target}, past {minutes} minutes).",
    )

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

        await client.send_message(
            bot_chat_id,
            f"📦 Batch {bi}/{len(batches)}: {len(batch_ids)} items",
        )

        # Download thumbnails to temp files, oldest → newest
        thumb_paths: List[str] = []
        thumb_dir = _ensure_thumb_dir()

        for mid in sorted(batch_ids):  # ascending msg_id = oldest first
            msg_obj = batch_msg_map[mid]
            it = batch_items[mid]

            thumb_data = None
            if it.kind == "photo":
                thumb_data = await _photo_thumb_bytes(_bot.client, msg_obj)
            elif it.kind in {"video", "video_note"}:
                thumb_data = await _video_thumb_bytes(_bot.client, msg_obj)

            if not thumb_data:
                continue

            tmp_path = os.path.join(
                thumb_dir, f"send_thumb_{mid}_{secrets.token_hex(4)}.jpg"
            )
            with open(tmp_path, "wb") as f:
                f.write(thumb_data)
            thumb_paths.append(tmp_path)

        # Send thumbnails to user
        if len(thumb_paths) == 1:
            await client.send_photo(bot_chat_id, thumb_paths[0])
        elif len(thumb_paths) >= 2:
            media_group = [InputMediaPhoto(p) for p in thumb_paths]
            await client.send_media_group(bot_chat_id, media_group)
        else:
            await client.send_message(
                bot_chat_id,
                "(No thumbnails available for this batch; you can still select items via the control panel.)",
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
            f"Control panel (Batch {bi}/{len(batches)}): tap items to select (✅ = selected), then press Download.",
            reply_markup=_build_control_keyboard(batch_req_id, batch_items),
        )
        req.control_msg_id = control_msg.id


async def handle_browse_callback(
    client: pyrogram.Client, query: pyrogram.types.CallbackQuery
):
    """Handle tgdl| callback queries from browse control panels."""
    _bot = _get_bot()

    try:
        _, req_id, msg_id_s, action = query.data.split("|")
        msg_id = int(msg_id_s)
    except Exception:
        await query.answer("Bad callback data", show_alert=True)
        return

    bot_chat_id = query.message.chat.id
    key = (bot_chat_id, req_id)
    req = _browse_reqs.get(key)

    if not req:
        await query.answer(
            "This selection has expired. Please send /browse again.", show_alert=True
        )
        return

    if time.time() - req.created_ts > 600:
        _browse_reqs.pop(key, None)
        await query.answer("Expired. Please send /browse again.", show_alert=True)
        return

    if action == "toggle":
        it = req.items.get(msg_id)
        if not it:
            await query.answer("Item not found", show_alert=True)
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
        await query.answer("Cancelled")
        await client.send_message(bot_chat_id, "Cancelled.")
        return

    if action == "done":
        selected_ids = [mid for mid, it in req.items.items() if it.selected]
        if not selected_ids:
            await query.answer("You haven't selected any items yet.", show_alert=True)
            return

        await query.answer("Starting download...")

        status_msg = await client.send_message(
            bot_chat_id,
            f"Downloading {len(selected_ids)} selected items...",
        )

        node = TaskNode(
            chat_id=req.source_chat_id,
            from_user_id=query.from_user.id,
            reply_message_id=status_msg.id,
            replay_message=f"Downloading {len(selected_ids)} selected items",
            limit=len(selected_ids),
            bot=_bot.bot,
            task_id=_bot.gen_task_id(),
        )
        node.client = _bot.client

        _bot.add_task_node(node)

        for mid in selected_ids:
            await _bot.add_download_task(req.msg_map[mid], node)

        node.is_running = True
        _browse_reqs.pop(key, None)


async def gc_browse_reqs_loop(interval_sec: int = 60, ttl_sec: int = 600):
    """Background task: garbage-collect expired BrowseRequests."""
    while True:
        now = time.time()
        expired = [
            k
            for k, req in list(_browse_reqs.items())
            if now - req.created_ts > ttl_sec
        ]
        for k in expired:
            _browse_reqs.pop(k, None)
        await asyncio.sleep(interval_sec)
