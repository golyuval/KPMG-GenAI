import logging
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir=None, max_bytes=5*1024*1024, backup_count=5):

    # ------ directory setup -------------------------------

    if log_dir is None:
        log_dir = os.environ.get("LOG_DIR", os.path.join("Part_2", "Log"))
    Path(log_dir).mkdir(exist_ok=True)

    # ------ files setup -------------------------------

    info_log_file = os.path.join(log_dir, "info.log")
    error_log_file = os.path.join(log_dir, "error.log")

    # ------ logger setup -------------------------------

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # ------ prevent duplicate handlers -------------------------------

    if logger.handlers:
        logging.warning("setup_logging called multiple times; handlers already exist. Skipping handler setup.")
        return logger

    # ------ formatters -------------------------------
    
    class TruncatingFormatter(logging.Formatter):
        def format(self, record):
            record.name = (record.name[:20]) if len(record.name) > 20 else record.name
            record.filename = (record.filename[:20]) if len(record.filename) > 20 else record.filename
            record.funcName = (record.funcName[:20]) if len(record.funcName) > 20 else record.funcName
            record.file_func_line = f"{record.filename} : {record.funcName} : {record.lineno}"[:49].ljust(49)
            return super().format(record)

    detailed_formatter = TruncatingFormatter(
        '%(asctime)s - %(levelname)-8s - %(file_func_line)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = TruncatingFormatter(
        '%(asctime)s - %(levelname)-8s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ------ console handler -------------------------------

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # ------ info handler with rotation -------------------------------

    info_file_handler = RotatingFileHandler(info_log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(detailed_formatter)
    info_file_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    
    # ------ error handler with rotation -------------------------------

    error_file_handler = RotatingFileHandler(error_log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    
    # ------ add handlers -------------------------------
    
    logger.addHandler(console_handler)
    logger.addHandler(info_file_handler)
    logger.addHandler(error_file_handler)
    
    return logger

def get_logger(module_name):
    return logging.getLogger(module_name)
