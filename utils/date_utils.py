# utils/date_utils.py
import logging

logger = logging.getLogger(__name__)

def format_datetime_exact(timestamp):
    return timestamp.date()