import logging
import os
from datetime import datetime
from pathlib import Path



def setup_logging(log_dir="Log"):

    Path(log_dir).mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    info_log_file = os.path.join(log_dir, f"info_{timestamp}.log")
    error_log_file = os.path.join(log_dir, f"error_{timestamp}.log")

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers = []

    # ------ formatters -------------------------------

    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
       
    # ------ console handler -------------------------------
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # ------ info handler -------------------------------
    
    info_file_handler = logging.FileHandler(info_log_file, encoding='utf-8')
    info_file_handler.setLevel(logging.INFO)
    info_file_handler.setFormatter(detailed_formatter)
    info_file_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    
    # ------ error handler -------------------------------
    
    error_file_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    
    # ------ add handlers -------------------------------
    
    logger.addHandler(console_handler)
    logger.addHandler(info_file_handler)
    logger.addHandler(error_file_handler)
    
    return logger

def get_module_logger(module_name):
    
    return logging.getLogger(module_name)