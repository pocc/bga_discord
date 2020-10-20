import logging
import re


class BGALoggingFormatter(logging.Formatter):
    """Remove passwords from log messages."""

    def format(self, record):
        record.msg = re.sub(r'\b(setup\s+\S+\s+)(\S+)', r'\1*HIDDEN*',
                            record.msg)
        return logging.Formatter.format(self, record)
