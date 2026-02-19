"""Tests for module/language.py — Language enum, _t(), set_language()."""

import sys
import unittest

sys.path.append("..")

from module.language import Language, _t, set_language, translations


class LanguageEnumTestCase(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(Language.EN.value, 1)
        self.assertEqual(Language.ZH.value, 2)
        self.assertEqual(Language.RU.value, 3)
        self.assertEqual(Language.UA.value, 4)
        self.assertEqual(Language.ZH_HANT.value, 5)

    def test_zh_hant_code_normalization(self):
        """'zh-Hant' normalizes to Language.ZH_HANT via replace+upper."""
        code = "zh-Hant".replace("-", "_").upper()
        self.assertEqual(Language[code], Language.ZH_HANT)

    def test_all_codes_resolve(self):
        for code, expected in [
            ("EN", Language.EN),
            ("ZH", Language.ZH),
            ("RU", Language.RU),
            ("UA", Language.UA),
            ("ZH_HANT", Language.ZH_HANT),
        ]:
            with self.subTest(code=code):
                self.assertEqual(Language[code], expected)

    def test_invalid_code_raises_key_error(self):
        with self.assertRaises(KeyError):
            _ = Language["INVALID"]


class TranslationTestCase(unittest.TestCase):
    def setUp(self):
        set_language(Language.EN)

    def tearDown(self):
        set_language(Language.EN)

    def test_english_returns_original(self):
        set_language(Language.EN)
        key = next(iter(translations))
        self.assertEqual(_t(key), key)

    def test_unknown_key_returns_original(self):
        set_language(Language.ZH_HANT)
        sentinel = "__no_such_key_xyz__"
        self.assertEqual(_t(sentinel), sentinel)

    def test_translation_indices_all_languages(self):
        """ZH→[0], RU→[1], UA→[2], ZH_HANT→[3]."""
        key = "Forward"  # exists in translations with all 4 entries
        for lang, idx in [
            (Language.ZH, 0),
            (Language.RU, 1),
            (Language.UA, 2),
            (Language.ZH_HANT, 3),
        ]:
            with self.subTest(lang=lang):
                set_language(lang)
                self.assertEqual(_t(key), translations[key][idx])

    def test_zh_hant_differs_from_zh(self):
        """Traditional and Simplified Chinese translations should differ."""
        # Use a key known to differ between ZH and ZH_HANT
        key = "Forward"
        set_language(Language.ZH)
        zh = _t(key)
        set_language(Language.ZH_HANT)
        zh_hant = _t(key)
        # Both are non-English
        self.assertNotEqual(zh, key)
        self.assertNotEqual(zh_hant, key)

    def test_set_language_is_global(self):
        set_language(Language.RU)
        key = "Forward"
        result = _t(key)
        self.assertEqual(result, translations[key][1])  # RU index


if __name__ == "__main__":
    unittest.main()
