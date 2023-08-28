from time import time
import logging

logger = logging.getLogger(__name__)


def timer(func):
    def wrap(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        logger.info(f"Function {func.__name__!r} executed in {t2 - t1}s")
        return result

    return wrap
