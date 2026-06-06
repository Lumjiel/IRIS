import logging
import os
import sys


_LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def get_logger(name: str) -> logging.Logger:
    """获取配置好的 logger 实例"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        ))
        logger.addHandler(handler)
        logger.setLevel(_LEVEL_MAP.get(_LOG_LEVEL, logging.INFO))
    return logger
