import logging, os, pathlib

# -------- paths ----------------------------------------------------

LOG_DIR = pathlib.Path(__file__).parent.parent / "Log"
LOG_DIR.mkdir(exist_ok=True)

INFO_FILE  = LOG_DIR / "log_info.log"
ERROR_FILE = LOG_DIR / "log_error.log"

# -------- root config (runs once on first import) ------------------

FMT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=FMT, handlers=[])

root = logging.getLogger()
root.handlers.clear()                     

# -------- console --------------------------------------------------

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter(FMT))
root.addHandler(ch)

# -------- info -----------------------------------------------------

fh_info = logging.FileHandler(INFO_FILE, mode="w", encoding="utf-8")
fh_info.setLevel(logging.INFO)
fh_info.setFormatter(logging.Formatter(FMT))
root.addHandler(fh_info)

# -------- error ----------------------------------------------------

fh_err = logging.FileHandler(ERROR_FILE, mode="w", encoding="utf-8")
fh_err.setLevel(logging.ERROR)
fh_err.setFormatter(logging.Formatter(FMT))
root.addHandler(fh_err)


def get_logger(name: str) -> logging.Logger:

    return logging.getLogger(name)
