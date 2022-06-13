import sys
import logging


def init_logging():
    logging.basicConfig(
        stream=sys.stderr, level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S"
    )
