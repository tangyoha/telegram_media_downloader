"""Util module to handle logs."""
import logging


class LogFilter(logging.Filter):
    """
    Custom Log Filter.

    Ignore logs from specific functions.
    """

    # pylint: disable = W0221
    def filter(self, record):
        if record.funcName in ("send", "get_file"):
            return False
        return True
