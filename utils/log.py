"""Util module to handle logs."""
import logging


class LogFilter(logging.Filter):
    """
    Custom Log Filter.

    Ignore logs from specific functions.
    """
    # pylint: disable = W0221
    def filter(self, log_record):
        if log_record.funcName == "send" or log_record.funcName == "get_file":
            return False
        return True
