
<h1 align="center">Telegram Media Downloader</h1>

<p align="center">
<a href="https://github.com/Dineshkarthik/Whatsapp-analyzer/blob/master/LICENSE"><img alt="License: MIT" src="https://black.readthedocs.io/en/stable/_static/license.svg"></a>
<a href="https://github.com/python/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

### Overview:
Download all media files from a conversation or a channel that you are a part of from telegram.
A meta of last read/downloaded message is stored in the config file so that in such a way it won't download the same media file again.

### Support:
| Category | Support |
|--|--|
|Language | `Python 3.4 ` and above|
|Download file types|  document|

### ToDo:
Add download support for
 - Photos
 - Videos
 - Audio files

### Installation

For *nix os distributions with `make` availability
```sh
$ git clone https://github.com/Dineshkarthik/telegram_media_downloader.git
$ cd telegram_media_downloader
$ make install
```
For Windows which doesn't have `make` inbuilt 
```sh
$ git clone https://github.com/Dineshkarthik/telegram_media_downloader.git
$ cd telegram_media_downloader
$ pip3 install -r requirements.txt
```

## Configuration 

**Getting your API Keys:**
The very first step requires you to obtain a valid Telegram API key (API id/hash pair):
1.  Visit  [https://my.telegram.org/apps](https://my.telegram.org/apps)  and log in with your Telegram Account.
2.  Fill out the form to register a new Telegram application. 
3.  Done! The API key consists of two parts:  **api_id**  and  **api_hash**.


**Getting chat id:**
1. Open https://web.telegram.org
2. Now go to the chat/channel and you will see the URL as something like
	- `https://web.telegram.org/#/im?p=u777000_6153771045853` here `u777000_6153771045853` is the chat id.
	- `https://web.telegram.org/#/im?p=@somename` here `somename` is the chat id.

```yaml
api_hash: your_api_hash
api_id: your_api_id
chat_id: telegram_chat_id
last_read_message_id: 0
```

- api_hash  - The api_hash you got from telegram apps
- api_id - The api_id you got from telegram apps
- chat_id -  The id of the chat/channel you want to download media. Which you get from the above-mentioned steps.
- last_read_message_id - If it is the first time you are going to read the channel let it be `0` or if you have already used this script to download media it will have some numbers which are auto-updated after the scripts successful execution. Don't change it.
## Execution
```sh
$ python3 media_downloader.py
```
All the documents will be stored inside a direcotry named `documents/` in the same path as the pythin script.