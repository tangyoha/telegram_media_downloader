"""Application module"""
import os
from typing import List

import yaml

# pylint: disable = R0902


class Application:
    """Application load config and update config."""

    def __init__(self, config_file: str):
        """
        Init and update telegram media downloader config

        Parameters
        ----------
        config_file: str
            config file name
        """
        self.config_file = config_file

        self.reset()

        try:
            with open(os.path.join(os.path.abspath("."), self.config_file)) as f:
                self.config = yaml.safe_load(f)
                self.load_config(self.config)
        except Exception:
            pass

    def reset(self):
        """reset Application"""
        # TODO: record total downlaod task
        self.total_download_task = 0
        self.downloaded_ids: list = []
        self.failed_ids: list = []
        self.disable_syslog: list = []
        self.save_path = os.path.abspath(".")
        self.ids_to_retry: list = []
        self.api_id: str = ""
        self.api_hash: str = ""
        self.chat_id: str = ""
        self.media_types: List[str] = []
        self.file_formats: dict = {}
        self.proxy: dict = {}
        self.last_read_message_id = 0
        self.restart_program = False
        self.config: dict = {}
        self.file_path_prefix: List[str] = ["chat_title", "media_datetime"]

    def load_config(self, _config: dict) -> bool:
        """load config from str.

        Parameters
        ----------
        _config: dict
            application config dict

        Returns
        -------
        bool
        """

        # TODO: jugde the storge if enough,and provide more path
        if _config.get("save_path") is not None:
            self.save_path = _config["save_path"]

        if _config.get("disable_syslog") is not None:
            self.disable_syslog = _config["disable_syslog"]

        self.last_read_message_id = _config["last_read_message_id"]
        if _config.get("ids_to_retry"):
            self.ids_to_retry = _config["ids_to_retry"]

        self.ids_to_retry_dict: dict = {}
        for it in self.ids_to_retry:
            self.ids_to_retry_dict[it] = True

        self.api_id = _config["api_id"]
        self.api_hash = _config["api_hash"]
        self.chat_id = _config["chat_id"]
        self.media_types = _config["media_types"]
        self.file_formats = _config["file_formats"]

        # option
        if _config.get("proxy"):
            self.proxy = _config["proxy"]
        if _config.get("restart_program"):
            self.restart_program = _config["restart_program"]
        if _config.get("file_path_prefix"):
            self.file_path_prefix = _config["file_path_prefix"]
        return True

    def get_file_save_path(
        self, media_type: str, chat_title: str, media_datetime: str
    ) -> str:
        """Get file save path prefix.

        Parameters
        ----------
        media_type: str
            see config.yaml media_types

        chat_title: str
            see channel or group title

        media_datetime: str
            media datatime

        Returns
        -------
        str
            file save path prefix
        """

        res: str = self.save_path
        for iter in self.file_path_prefix:
            if iter == "chat_title":
                res = os.path.join(res, chat_title)
            elif iter == "media_datetime":
                res = os.path.join(res, media_datetime)
            elif iter == "media_type":
                res = os.path.join(res, media_type)
        return res

    def need_skip_message(self, message_id: int) -> bool:
        """if need skip download message.

        Parameters
        ----------
        message_id: int
            readly to download meesage id

        Returns
        -------
        bool
        """
        return self.ids_to_retry_dict.get(message_id) is not None

    def update_config(self, immediate: bool = True):
        """update config

        Parameters
        ----------
        immediate: bool
            If update config immediate,default True
        """

        # pylint: disable = W0201
        self.ids_to_retry = (
            list(set(self.ids_to_retry) - set(self.downloaded_ids)) + self.failed_ids
        )

        self.config["last_read_message_id"] = self.last_read_message_id
        self.config["ids_to_retry"] = self.ids_to_retry
        self.config["disable_syslog"] = self.disable_syslog
        self.config["save_path"] = self.save_path
        self.config["file_path_prefix"] = self.file_path_prefix

        if immediate:
            with open(self.config_file, "w") as yaml_file:
                yaml.dump(self.config, yaml_file, default_flow_style=False)
