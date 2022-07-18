"""Utility module to manage meta info."""
import platform

from rich.console import Console

from . import __copyright__, __license__, __version__

APP_VERSION = f"Telegram Media Downloader {__version__}"
DEVICE_MODEL = f"{platform.python_implementation()} {platform.python_version()}"
SYSTEM_VERSION = f"{platform.system()} {platform.release()}"
LANG_CODE = "en"


def print_meta(logger):
    """Prints meta-data of the downloader script."""
    console = Console()
    # pylint: disable = C0301
    console.log(
        f"[bold]Telegram Media Downloader v{__version__}[/bold],\n[i]{__copyright__}[/i]"
    )
    console.log(f"Licensed under the terms of the {__license__}", end="\n\n")
    logger.info(f"Device: {DEVICE_MODEL} - {APP_VERSION}")
    logger.info(f"System: {SYSTEM_VERSION} ({LANG_CODE.upper()})")
