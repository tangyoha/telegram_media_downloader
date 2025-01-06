"""Utility module to check for new release of telegram-media-downloader"""
import json

import requests  # type: ignore
from loguru import logger
from rich.console import Console
from rich.markdown import Markdown

from . import __version__


# pylint: disable = C0301
def get_latest_release(proxy_config: dict = None) -> dict:
    """
    Get the latest release information.

    :param proxy_config: A dictionary containing proxy configuration settings (default: {}).
    :type proxy_config: dict
    :return: A dictionary containing the latest release information.
    :rtype: dict
    """
    headers: dict = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
    }

    if proxy_config:
        scheme = proxy_config.get("scheme", "")
        hostname = proxy_config.get("hostname", "")
        port = proxy_config.get("port", "")
        username = proxy_config.get("username")
        password = proxy_config.get("password")

    proxies = {}
    if proxy_config:
        proxies = {
            "http": f"{scheme}://{hostname}:{port}",
            "https": f"{scheme}://{hostname}:{port}",
        }

        if username and password:
            proxies["http"] = f"{scheme}://{username}:{password}@{hostname}:{port}"
            proxies["https"] = f"{scheme}://{username}:{password}@{hostname}:{port}"
    try:
        response = requests.get(
            url="https://api.github.com/repos/tangyoha/telegram_media_downloader/releases/latest",
            headers=headers,
            proxies=proxies,
            timeout=60,
        )

    except Exception as e:
        logger.warning(f"{e}")
        return {}

    latest_release: dict = json.loads(response.text)

    if f"v{__version__}" != latest_release["tag_name"]:
        return latest_release

    return {}


def check_for_updates(proxy_config: dict = None):
    """Checks for new releases.

    Using Github API checks for new release and prints information of new release if available.
    """
    console = Console()
    latest_release = get_latest_release(proxy_config)
    try:
        if latest_release:
            update_message: str = (
                f"## New version of Telegram-Media-Downloader is available - {latest_release['name']}\n"
                f"You are using an outdated version v{__version__} please pull in the changes using `git pull` or download the latest release.\n\n"
                f"Find more details about the latest release here - {latest_release['html_url']}"
            )
            console.print(Markdown(update_message))
    except Exception as e:
        logger.warning(f"{e}")
