from distutils.core import setup

from utils import __version__

setup(
    name="telegram-media-downloader",
    version=__version__,
    author="tangyoha",
    author_email="tangyoha@outlook.com",
    description="A simple script to download media from telegram",
    url="https://github.com/tangyoha/telegram_media_downloader",
    download_url="https://github.com/tangyoha/telegram_media_downloader/releases/latest",
    py_modules=["media_downloader"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet",
        "Topic :: Communications",
        "Topic :: Communications :: Chat",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    project_urls={
        "Tracker": "https://github.com/tangyoha/telegram_media_downloader/issues",
        "Community": "https://t.me/TeegramMediaDownload",
        "Source": "https://github.com/tangyoha/telegram_media_downloader",
    },
    python_requires="~=3.7",
)
