"""Utility module to check for new release of telegram-media-downloader"""
import http.client
import json

from rich.console import Console
from rich.markdown import Markdown

from . import __version__


# pylint: disable = C0301
def check_for_updates() -> None:
    """Checks for new releases.

    Using Github API checks for new release and prints information of new release if available.
    """
    console = Console()
    try:
        headers: dict = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
        }
        conn = http.client.HTTPSConnection("api.github.com")
        conn.request(
            method="GET",
            url="/repos/tangyoha/telegram_media_downloader/releases/latest",
            headers=headers,
        )
        res = conn.getresponse()
        latest_release: dict = json.loads(res.read().decode("utf-8"))
        if f"{__version__}" != latest_release["tag_name"]:
            update_message: str = (
                f"## New version of Telegram-Media-Downloader is available - {latest_release['name']}\n"
                f"You are using an outdated version v{__version__} please pull in the changes using `git pull` or download the latest release.\n\n"
                f"Find more details about the latest release here - {latest_release['html_url']}"
            )
            console.print(Markdown(update_message))
    except Exception as e:
        console.log(
            f"Following error occured when checking for updates\n{e.__class__}, {e}"
        )
