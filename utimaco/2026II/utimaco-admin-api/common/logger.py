"""
日志模块 — 控制台 + 滚动文件双输出。
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from config import config


def _setup_logger():
    log_dir = os.path.join(config.root_dir, config.get("paths.log_dir", "logs"))
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("utimaco")
    logger.setLevel(getattr(logging, config.get("log.level", "INFO")))

    fmt = logging.Formatter(
        config.get("log.format", "%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    )

    # 控制台
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # 文件（10 MB 滚动 × 5）
    fh = RotatingFileHandler(
        os.path.join(log_dir, "test.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


logger = _setup_logger()
