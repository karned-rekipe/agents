import logging
from types import FrameType

import sys
from loguru import logger

_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"

_STDLIB_LOGGERS = (
    "httpx",
    "httpcore",
    "asyncio",
    "uvicorn",
    "uvicorn.access",
    "uvicorn.error",
    "chainlit",
)


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame: FrameType | None = sys._getframe(6)
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth = depth, exception = record.exc_info).log(level, record.getMessage())


def setup_logging(level: str = "DEBUG") -> None:
    logger.remove()
    logger.add(sys.stderr, format = _FORMAT, level = level)

    for name in _STDLIB_LOGGERS:
        log = logging.getLogger(name)
        log.setLevel(logging.DEBUG)
        log.handlers = [_InterceptHandler()]
        log.propagate = False

    logging.root.setLevel(logging.WARNING)
