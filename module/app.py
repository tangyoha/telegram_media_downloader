"""Application module"""

import os
from typing import List, Optional

import yaml

from module.cloud_drive import CloudDrive, CloudDriveConfig
from module.filter import Filter
from utils.format import replace_date_time
from utils.meta_data import MetaData

# pylint: disable = R0902


class Application:
    """Application load config and update config."""

    def __init__(
        self,
        config_file: str,
        app_data_file: str,
        application_name: str = "UndefineApp",
    ):
        """
        Init and update telegram media downloader config

        Parameters
        ----------
        config_file: str
            Config file name

        app_data_file: str
            App data file

        application_name: str
            Application Name

        """
        self.config_file: str = config_file
        self.app_data_file: str = app_data_file
        self.application_name: str = application_name
        self.download_filter = Filter()

        # TODO: record total download task
        self.total_download_task = 0
        self.downloaded_ids: list = []
        # self.already_download_ids_set = set()
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
        self.app_data: dict = {}
        self.file_path_prefix: List[str] = ["chat_title", "media_datetime"]
        self.file_name_prefix: List[str] = ["message_id", "file_name"]
        self.file_name_prefix_split: str = " - "
        self.log_file_path = os.path.join(os.path.abspath("."), "log")
        self.cloud_drive_config = CloudDriveConfig()
        self.hide_file_name = False
        self.caption_name_dict: dict = {}
        self.max_concurrent_transmissions: int = 1
        self.web_host: str = "localhost"
        self.web_port: int = 5000
        self.download_filter_dict: dict = {}
        self.ids_to_retry_dict: dict = {}
        self.session_name = self.application_name

    def assign_config(self, _config: dict) -> bool:
        """assign config from str.

        Parameters
        ----------
        _config: dict
            application config dict

        Returns
        -------
        bool
        """
        # pylint: disable = R0912
        # TODO: judge the storage if enough,and provide more path
        if _config.get("save_path") is not None:
            self.save_path = _config["save_path"]

        if _config.get("disable_syslog") is not None:
            self.disable_syslog = _config["disable_syslog"]

        self.last_read_message_id = _config["last_read_message_id"]
        if _config.get("ids_to_retry"):
            self.ids_to_retry = _config["ids_to_retry"]

        self.ids_to_retry_dict = {}
        for it in self.ids_to_retry:
            self.ids_to_retry_dict[it] = True

        self.api_id = _config["api_id"]
        self.api_hash = _config["api_hash"]
        self.chat_id = _config["chat_id"]
        self.media_types = _config["media_types"]
        self.file_formats = _config["file_formats"]

        self.hide_file_name = _config.get("hide_file_name", False)

        # option
        if _config.get("proxy"):
            self.proxy = _config["proxy"]
        if _config.get("restart_program"):
            self.restart_program = _config["restart_program"]
        if _config.get("file_path_prefix"):
            self.file_path_prefix = _config["file_path_prefix"]
        if _config.get("file_name_prefix"):
            self.file_name_prefix = _config["file_name_prefix"]

        if _config.get("upload_drive"):
            upload_drive_config = _config["upload_drive"]
            if upload_drive_config.get("enable_upload_file"):
                self.cloud_drive_config.enable_upload_file = upload_drive_config[
                    "enable_upload_file"
                ]

            if upload_drive_config.get("rclone_path"):
                self.cloud_drive_config.rclone_path = upload_drive_config["rclone_path"]

            if upload_drive_config.get("remote_dir"):
                self.cloud_drive_config.remote_dir = upload_drive_config["remote_dir"]

            if upload_drive_config.get("before_upload_file_zip"):
                self.cloud_drive_config.before_upload_file_zip = upload_drive_config[
                    "before_upload_file_zip"
                ]

            if upload_drive_config.get("after_upload_file_delete"):
                self.cloud_drive_config.after_upload_file_delete = upload_drive_config[
                    "after_upload_file_delete"
                ]

            if upload_drive_config.get("upload_adapter"):
                self.cloud_drive_config.upload_adapter = upload_drive_config[
                    "upload_adapter"
                ]

        self.file_name_prefix_split = _config.get(
            "file_name_prefix_split", self.file_name_prefix_split
        )
        self.web_host = _config.get("web_host", self.web_host)
        self.web_port = _config.get("web_port", self.web_port)

        self.download_filter_dict = _config.get(
            "download_filter", self.download_filter_dict
        )

        for key, value in self.download_filter_dict.items():
            self.download_filter_dict[key] = replace_date_time(value)

        # TODO: add check if expression exist syntax error

        self.max_concurrent_transmissions = _config.get(
            "max_concurrent_transmissions", self.max_concurrent_transmissions
        )

        return True

    def assign_app_data(self, app_data: dict) -> bool:
        """Assign config from str.

        Parameters
        ----------
        app_data: dict
            application data dict

        Returns
        -------
        bool
        """

        if app_data.get("ids_to_retry"):
            # check old config.yaml exist
            if len(self.ids_to_retry) > 0:
                self.ids_to_retry.extend(list(app_data["ids_to_retry"]))
            else:
                self.ids_to_retry = app_data["ids_to_retry"]

        # if app_data.get("already_download_ids"):
        #    self.already_download_ids_set = set(app_data["already_download_ids"])
        return True

    def upload_file(self, local_file_path: str):
        """Upload file"""
        return CloudDrive.upload_file(
            self.cloud_drive_config, self.save_path, local_file_path
        )

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
            media datetime

        Returns
        -------
        str
            file save path prefix
        """

        res: str = self.save_path
        for prefix in self.file_path_prefix:
            if prefix == "chat_title":
                res = os.path.join(res, chat_title)
            elif prefix == "media_datetime":
                res = os.path.join(res, media_datetime)
            elif prefix == "media_type":
                res = os.path.join(res, media_type)
        return res

    def get_file_name(
        self, message_id: int, file_name: Optional[str], caption: Optional[str]
    ) -> str:
        """Get file save path prefix.

        Parameters
        ----------
        message_id: int
            Message id

        file_name: Optional[str]
            File name

        caption: Optional[str]
            Message caption

        Returns
        -------
        str
            File name
        """

        res: str = ""
        for prefix in self.file_name_prefix:
            if prefix == "message_id":
                if res != "":
                    res += self.file_name_prefix_split
                res += f"{message_id}"
            elif prefix == "file_name" and file_name:
                if res != "":
                    res += self.file_name_prefix_split
                res += f"{file_name}"
            elif prefix == "caption" and caption:
                if res != "":
                    res += self.file_name_prefix_split
                res += f"{caption}"
        if res == "":
            res = f"{message_id}"
        return res

    def need_skip_message(
        self, chat_id: str, message_id: int, meta_data: MetaData
    ) -> bool:
        """if need skip download message.

        Parameters
        ----------
        chat_id: str
            Config.yaml defined

        message_id: int
            Readily to download message id

        meta_data: MetaData
            Ready to match filter

        Returns
        -------
        bool
        """
        if message_id in self.ids_to_retry_dict:
            return True

        if chat_id in self.download_filter_dict:
            self.download_filter.set_meta_data(meta_data)
            exec_res = not self.download_filter.exec(self.download_filter_dict[chat_id])
            return exec_res

        return False

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
        self.config["disable_syslog"] = self.disable_syslog
        self.config["save_path"] = self.save_path
        self.config["file_path_prefix"] = self.file_path_prefix

        if self.config.get("ids_to_retry"):
            self.config.pop("ids_to_retry")

        self.app_data["ids_to_retry"] = self.ids_to_retry

        # for it in self.downloaded_ids:
        #    self.already_download_ids_set.add(it)

        # self.app_data["already_download_ids"] = list(self.already_download_ids_set)

        if immediate:
            with open(self.config_file, "w", encoding="utf-8") as yaml_file:
                yaml.dump(
                    self.config,
                    yaml_file,
                    default_flow_style=False,
                    encoding="utf-8",
                    allow_unicode=True,
                )

        if immediate:
            with open(self.app_data_file, "w", encoding="utf-8") as yaml_file:
                yaml.dump(
                    self.app_data,
                    yaml_file,
                    default_flow_style=False,
                    encoding="utf-8",
                    allow_unicode=True,
                )

    def load_config(self):
        """Load user config"""
        with open(
            os.path.join(os.path.abspath("."), self.config_file), encoding="utf-8"
        ) as f:
            self.config = yaml.load(f.read(), Loader=yaml.FullLoader)
            self.assign_config(self.config)

        with open(
            os.path.join(os.path.abspath("."), self.app_data_file), encoding="utf-8"
        ) as f:
            self.app_data = yaml.load(f.read(), Loader=yaml.FullLoader)
            self.assign_app_data(self.app_data)

    def pre_run(self):
        """before run application do"""
        self.cloud_drive_config.pre_run()

    def set_caption_name(
        self, chat_id: str, media_group_id: Optional[str], caption: str
    ):
        """set caption name map

        Parameters
        ----------
        chat_id: str
            Unique identifier for this chat.

        media_group_id: Optional[str]
            The unique identifier of a media message group this message belongs to.

        caption: str
            Caption for the audio, document, photo, video or voice, 0-1024 characters.
        """
        if not media_group_id:
            return

        if chat_id in self.caption_name_dict:
            self.caption_name_dict[chat_id][media_group_id] = caption
        else:
            self.caption_name_dict[chat_id] = {media_group_id: caption}

    def get_caption_name(
        self, chat_id: str, media_group_id: Optional[str]
    ) -> Optional[str]:
        """set caption name map
                media_group_id: Optional[str]
            The unique identifier of a media message group this message belongs to.

        caption: str
            Caption for the audio, document, photo, video or voice, 0-1024 characters.
        """

        if (
            not media_group_id
            or chat_id not in self.caption_name_dict
            or media_group_id not in self.caption_name_dict[chat_id]
        ):
            return None

        return str(self.caption_name_dict[chat_id][media_group_id])
