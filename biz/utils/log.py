import logging
import os


class CustomLogger(logging.Logger):
    def warn(self, msg, *args, **kwargs):
        super().warning(f"⚠️ {msg}", *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        super().error(f"❌ {msg}", *args, **kwargs)


log_level = os.environ.get("LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, log_level.upper(), logging.INFO)

logger = CustomLogger(__name__)
logger.setLevel(LOG_LEVEL)
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s"
    )
)
logger.addHandler(_handler)
