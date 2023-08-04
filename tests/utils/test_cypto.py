"""Test Crypto"""

import sys
import unittest

from utils.crypto import AesBase64

sys.path.append("..")  # Adds higher directory to python modules path.


class TestAesBase64(unittest.TestCase):
    def test_aes_base64_encryption(self):
        key = "This is a key123"
        iv = "This is an iv456"
        aes = AesBase64(key, iv)
        content = "Some text for encryption."
        encrypted_content = aes.encrypt(content)
        decrypted_content = aes.decrypt(encrypted_content)
        self.assertEqual(content, decrypted_content)

    def test_aes_base64_encryption_with_special_characters(self):
        key = "Special!@#$%^&*("
        iv = "Characters123456"
        aes = AesBase64(key, iv)
        content = "Text with special characters!@#$%^&*()_+-=[]{}|;"
        encrypted_content = aes.encrypt(content)
        decrypted_content = aes.decrypt(encrypted_content)
        self.assertEqual(content, decrypted_content)

    def test_aes_base64_encryption_with_empty_string(self):
        key = "Empty string tes"
        iv = "1234567890123456"
        aes = AesBase64(key, iv)
        content = ""
        encrypted_content = aes.encrypt(content)
        decrypted_content = aes.decrypt(encrypted_content)
        self.assertEqual(content, decrypted_content)

    def test_aes_base64_pkcs7padding(self):
        key = "Test padding key"
        iv = "1234567890123456"
        aes = AesBase64(key, iv)
        content = "Test padding."
        padded_content = aes.pkcs7padding(content)
        self.assertEqual(len(padded_content) % 16, 0)
        self.assertEqual(padded_content[-1], chr(16 - len(content) % 16))

    def test_aes_base64_pkcs7unpadding(self):
        key = "Test unpadding key"
        iv = "1234567890123456"
        aes = AesBase64(key, iv)
        content = "Test unpadding."
        padded_content = aes.pkcs7padding(content)
        unpadded_content = aes.pkcs7unpadding(padded_content)
        self.assertEqual(unpadded_content, content)
