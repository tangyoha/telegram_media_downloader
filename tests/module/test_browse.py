"""Tests for module/browse.py — pure-logic functions (no Telegram API calls)."""

import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

sys.path.append("..")

from module.browse import (
    BrowseItem,
    BrowseRequest,
    _build_control_keyboard,
    _get_media_kind,
    _get_sender_label,
    _normalize_target,
    _parse_browse_args,
)


class NormalizeTargetTestCase(unittest.TestCase):
    def test_at_handle_preserved(self):
        self.assertEqual(_normalize_target("@channel"), "@channel")

    def test_bare_name_gets_prefix(self):
        self.assertEqual(_normalize_target("channel"), "@channel")

    def test_numeric_id_unchanged(self):
        self.assertEqual(_normalize_target("123456789"), "123456789")

    def test_negative_id_unchanged(self):
        self.assertEqual(_normalize_target("-1001234567890"), "-1001234567890")

    def test_t_me_url(self):
        self.assertEqual(_normalize_target("https://t.me/mychannel"), "@mychannel")

    def test_telegram_me_url(self):
        self.assertEqual(_normalize_target("https://telegram.me/mychannel"), "@mychannel")

    def test_http_url(self):
        self.assertEqual(_normalize_target("http://t.me/mychannel"), "@mychannel")

    def test_whitespace_stripped(self):
        self.assertEqual(_normalize_target("  @channel  "), "@channel")

    def test_empty_string(self):
        result = _normalize_target("")
        self.assertIsInstance(result, str)


class ParseBrowseArgsTestCase(unittest.TestCase):
    def test_valid_at_target(self):
        self.assertEqual(_parse_browse_args("@chan 30"), ("@chan", 30))

    def test_valid_m_suffix(self):
        self.assertEqual(_parse_browse_args("@chan 30m"), ("@chan", 30))

    def test_valid_min_suffix(self):
        result = _parse_browse_args("@chan 30 min")
        self.assertEqual(result, ("@chan", 30))

    def test_valid_minutes_suffix(self):
        result = _parse_browse_args("@chan 60 minutes")
        self.assertEqual(result, ("@chan", 60))

    def test_numeric_target(self):
        result = _parse_browse_args("-1001234567890 10")
        self.assertEqual(result, ("-1001234567890", 10))

    def test_url_target(self):
        result = _parse_browse_args("https://t.me/mychan 45")
        self.assertEqual(result, ("@mychan", 45))

    def test_returns_none_on_empty(self):
        self.assertIsNone(_parse_browse_args(""))

    def test_returns_none_on_missing_minutes(self):
        self.assertIsNone(_parse_browse_args("@chan"))

    def test_returns_none_on_non_numeric_minutes(self):
        self.assertIsNone(_parse_browse_args("@chan abc"))

    def test_returns_none_on_none_input(self):
        self.assertIsNone(_parse_browse_args(None))


class GetMediaKindTestCase(unittest.TestCase):
    def _msg(self, **kwargs):
        m = MagicMock()
        m.photo = kwargs.get("photo", None)
        m.video = kwargs.get("video", None)
        m.video_note = kwargs.get("video_note", None)
        return m

    def test_photo(self):
        self.assertEqual(_get_media_kind(self._msg(photo=object())), "photo")

    def test_video(self):
        self.assertEqual(_get_media_kind(self._msg(video=object())), "video")

    def test_video_note(self):
        self.assertEqual(_get_media_kind(self._msg(video_note=object())), "video_note")

    def test_no_media(self):
        self.assertEqual(_get_media_kind(self._msg()), "")

    def test_photo_priority_over_video(self):
        # photo is checked first in the function
        msg = self._msg(photo=object(), video=object())
        self.assertEqual(_get_media_kind(msg), "photo")

    def test_video_note_priority_over_video(self):
        msg = self._msg(video=object(), video_note=object())
        self.assertEqual(_get_media_kind(msg), "video_note")


class GetSenderLabelTestCase(unittest.TestCase):
    def _user_msg(self, username=None, first_name=None, user_id=42):
        user = MagicMock()
        user.username = username
        user.first_name = first_name
        user.id = user_id
        msg = MagicMock()
        msg.from_user = user
        msg.sender_chat = None
        return msg

    def _chat_msg(self, username=None, title=None, chat_id=99):
        chat = MagicMock()
        chat.username = username
        chat.title = title
        chat.id = chat_id
        msg = MagicMock()
        msg.from_user = None
        msg.sender_chat = chat
        return msg

    def test_user_with_username(self):
        self.assertEqual(_get_sender_label(self._user_msg(username="alice")), "@alice")

    def test_user_with_first_name_only(self):
        self.assertEqual(_get_sender_label(self._user_msg(first_name="Bob")), "Bob")

    def test_user_with_id_only(self):
        msg = self._user_msg(user_id=12345)
        self.assertEqual(_get_sender_label(msg), "12345")

    def test_sender_chat_with_username(self):
        self.assertEqual(_get_sender_label(self._chat_msg(username="news")), "news")

    def test_sender_chat_with_title(self):
        self.assertEqual(
            _get_sender_label(self._chat_msg(title="News Channel")), "News Channel"
        )

    def test_sender_chat_with_id_only(self):
        msg = self._chat_msg(chat_id=777)
        self.assertEqual(_get_sender_label(msg), "777")

    def test_no_sender(self):
        msg = MagicMock()
        msg.from_user = None
        msg.sender_chat = None
        self.assertEqual(_get_sender_label(msg), "unknown")


class BrowseItemDefaultsTestCase(unittest.TestCase):
    def test_defaults(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        item = BrowseItem(msg_id=1, kind="photo", date_utc=dt, sender="@user")
        self.assertFalse(item.selected)
        self.assertFalse(item.downloaded)

    def test_explicit_values(self):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        item = BrowseItem(1, "video", dt, "@user", selected=True, downloaded=True)
        self.assertTrue(item.selected)
        self.assertTrue(item.downloaded)


class BrowseRequestDefaultsTestCase(unittest.TestCase):
    def test_field_defaults(self):
        req = BrowseRequest(
            source_chat_id=1,
            created_ts=0.0,
            target="@chan",
            minutes=10,
            items={},
            msg_map={},
        )
        self.assertIsNone(req.control_msg_id)
        self.assertIsNone(req.batch_header_msg_id)
        self.assertEqual(req.thumb_msg_ids, [])

    def test_thumb_msg_ids_not_shared(self):
        """Each BrowseRequest gets its own thumb_msg_ids list."""
        r1 = BrowseRequest(1, 0.0, "@a", 10, {}, {})
        r2 = BrowseRequest(2, 0.0, "@b", 10, {}, {})
        r1.thumb_msg_ids.append(99)
        self.assertEqual(r2.thumb_msg_ids, [])


class BuildControlKeyboardTestCase(unittest.TestCase):
    def _item(self, msg_id, selected=False, downloaded=False):
        dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
        return BrowseItem(
            msg_id=msg_id,
            kind="photo",
            date_utc=dt,
            sender="@u",
            selected=selected,
            downloaded=downloaded,
        )

    def _get_buttons(self, items, **kwargs):
        kb = _build_control_keyboard("req123", items, **kwargs)
        return kb.inline_keyboard  # list of rows

    def test_unselected_label(self):
        rows = self._get_buttons({10: self._item(10)})
        labels = [btn.text for btn in rows[0]]
        self.assertIn("⬜#10", labels)

    def test_selected_label(self):
        rows = self._get_buttons({10: self._item(10, selected=True)})
        labels = [btn.text for btn in rows[0]]
        self.assertIn("✅#10", labels)

    def test_downloaded_label(self):
        rows = self._get_buttons({10: self._item(10, downloaded=True)})
        labels = [btn.text for btn in rows[0]]
        self.assertIn("📥#10", labels)

    def test_callback_data_format(self):
        rows = self._get_buttons({10: self._item(10)})
        btn = rows[0][0]
        self.assertEqual(btn.callback_data, "tgdl|req123|10|toggle")

    def test_action_row_has_download_and_cancel(self):
        rows = self._get_buttons({10: self._item(10)})
        last_row = rows[-1]
        texts = [b.text for b in last_row]
        self.assertTrue(any("Download" in t or "📥" in t for t in texts))
        self.assertTrue(any("Cancel" in t or "❌" in t for t in texts))

    def test_action_row_callback_data(self):
        rows = self._get_buttons({10: self._item(10)})
        last_row = rows[-1]
        callbacks = [b.callback_data for b in last_row]
        self.assertIn("tgdl|req123|0|done", callbacks)
        self.assertIn("tgdl|req123|0|cancel", callbacks)

    def test_per_row_grouping(self):
        items = {i: self._item(i) for i in range(7)}
        rows = self._get_buttons(items, per_row=3)
        # Items: rows of 3,3,1 + 1 action row = 4 rows
        item_rows = rows[:-1]
        self.assertEqual(len(item_rows[0]), 3)
        self.assertEqual(len(item_rows[1]), 3)
        self.assertEqual(len(item_rows[2]), 1)

    def test_sorted_by_msg_id(self):
        items = {30: self._item(30), 10: self._item(10), 20: self._item(20)}
        rows = self._get_buttons(items, per_row=10)
        ids_in_order = [int(b.text.lstrip("⬜✅📥#")) for b in rows[0]]
        self.assertEqual(ids_in_order, [10, 20, 30])


if __name__ == "__main__":
    unittest.main()
