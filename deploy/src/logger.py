"""Logging configuration for Shanghan-TCM v1."""

import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(name="shanghan", log_dir=None, level=logging.INFO):
    """Setup logging with console and file handlers."""
    
    if log_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(script_dir, 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    log_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    log_file = os.path.join(log_dir, f'shanghan_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name=None):
    """Get a logger instance."""
    if name:
        return logging.getLogger(f"shanghan.{name}")
    return logging.getLogger("shanghan")


def log_request(logger, method, path, status=None, duration=None):
    """Log HTTP request."""
    msg = f"REQUEST | {method} {path}"
    if status:
        msg += f" | Status: {status}"
    if duration:
        msg += f" | Duration: {duration:.3f}s"
    logger.info(msg)


def log_error(logger, error, context=None):
    """Log error with context."""
    msg = f"ERROR | {type(error).__name__}: {error}"
    if context:
        msg += f" | Context: {context}"
    logger.error(msg, exc_info=True)


def log_api_call(logger, endpoint, params=None, response=None, error=None):
    """Log API call."""
    msg = f"API_CALL | {endpoint}"
    if params:
        msg += f" | Params: {params}"
    if response:
        msg += f" | Response: {response}"
    if error:
        msg += f" | Error: {error}"
    logger.info(msg)


def log_user_action(logger, user, action, details=None):
    """Log user action."""
    msg = f"USER_ACTION | User: {user} | Action: {action}"
    if details:
        msg = f"{msg} | Details: {details}"
    logger.info(msg)
