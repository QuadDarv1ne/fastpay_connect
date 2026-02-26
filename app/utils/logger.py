import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO", max_bytes: int = 10_000_000, backup_count: int = 5):
    """
    Настраивает логирование с ротацией файлов.
    
    :param level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :param max_bytes: Максимальный размер файла лога перед ротацией (по умолчанию 10MB)
    :param backup_count: Количество резервных файлов лога
    """
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    if root_logger.handlers:
        return
    
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    error_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
