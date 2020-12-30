"""Utility module to manage meta info."""
import platform

from . import __version__, __copyright__, __license__

APP_VERSION = f"Telegram Media Downloader {__version__}"
DEVICE_MODEL = (
    f"{platform.python_implementation()} {platform.python_version()}"
)
SYSTEM_VERSION = f"{platform.system()} {platform.release()}"
LANG_CODE = "en"


def print_meta(logger):
    """Prints meta-data of the downloader script."""
    print(f"Telegram Media Downloader v{__version__}, {__copyright__}")
    print(f"Licensed under the terms of the {__license__}", end="\n\n")
    logger.info(f"Device: {DEVICE_MODEL} - {APP_VERSION}")
    logger.info(f"System: {SYSTEM_VERSION} ({LANG_CODE.upper()})")
