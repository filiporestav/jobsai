import sys

from datetime import datetime
import logging

from settings import LOG_LEVEL, LOG_DATE_FORMAT, LOG_FORMAT, DATE_FORMAT, TIMESTAMP_FILE

log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=LOG_LEVEL, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)


def elapsed_time(start):
    return datetime.now() - start


def timestamp_now():
    return datetime.now().strftime(DATE_FORMAT)


def write_timestamp(timestamp=None):
    if not timestamp:
        timestamp = timestamp_now()
    with open(file=TIMESTAMP_FILE, mode='w') as f:
        f.write(timestamp)
    log.info(f"New timestamp written: {timestamp}")
    return timestamp


def read_timestamp():
    with open(file=TIMESTAMP_FILE, mode='r') as f:
        timestamp = f.read()
    return timestamp.strip('\n')
