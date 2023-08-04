"""Crypto utils"""

import base64

from Crypto.Cipher import AES


class AesBase64(object):
    """for AES encryption"""

    def __init__(self, key: str, iv: str):
        self.key = key.encode("utf-8")
        self.iv = iv.encode("utf-8")
        self.mode = AES.MODE_CBC

    def encrypt(self, content):
        """
        Encrypts the given content using the AES encryption algorithm.

        Parameters:
            content (str): The content to be encrypted.

        Returns:
            str: The encrypted content encoded in base64.
        """
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        content_padding = self.pkcs7padding(content)
        encrypt_bytes = cipher.encrypt(content_padding.encode("utf-8"))
        return base64.b64encode(encrypt_bytes)

    def decrypt(self, content):
        """
        Decrypts the given content using AES encryption
        with Cipher Block Chaining (CBC) mode.

        Parameters:
            content (str): The content to be decrypted.

        Returns:
            str: The decrypted text.
        """
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        content = base64.b64decode(content)
        text = cipher.decrypt(content).decode("utf-8")
        return self.pkcs7unpadding(text)

    def pkcs7unpadding(self, text):
        """
        Removes the PKCS#7 padding from the given text.

        Parameters:
            text (str): The text to remove padding from.

        Returns:
            str: The text without PKCS#7 padding.
        """
        length = len(text)
        unpadding = ord(text[length - 1])
        return text[0 : length - unpadding]

    def pkcs7padding(self, text):
        """
        Adds PKCS7 padding to the given text.

        Args:
            text (str): The text to be padded.

        Returns:
            str: The padded text.
        """
        bs = 16
        length = len(text)
        bytes_length = len(text.encode("utf-8"))
        padding_size = length if (bytes_length == length) else bytes_length
        padding = bs - padding_size % bs
        padding_text = chr(padding) * padding
        return text + padding_text
