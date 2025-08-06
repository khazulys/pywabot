"""
This module provides a standardized logging configuration for the pywabot library.

It offers a flexible `setup_logging` function that allows consumers of the
library to easily configure the desired level of logging output, including
a 'silent' mode to disable all non-critical logs.
"""
import logging
import sys


def setup_logging(level='info'):
    """
    Configures the root logger for the pywabot library.

    This function sets up a stream handler to `sys.stdout` with a specific
    formatter. It also manages the logging level for both the library's
    logger and external libraries like `httpx` to reduce noise.

    Args:
        level (str): The desired logging level. Can be one of 'debug',
            'info', 'warning', 'error', 'critical', or 'silent'.
            Defaults to 'info'. If 'silent', all logging is disabled.

    Returns:
        None

    Example:
        >>> import logging
        >>> setup_logging('debug')
        >>> logging.getLogger("pywabot").debug("This is a test message.")
    """
    if level.lower() == 'silent':
        logging.disable(logging.CRITICAL)
        return

    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True,
    )

    # Re-enable logging if it was previously disabled
    logging.disable(logging.NOTSET)

    # Set httpx logger to a higher level to avoid excessive noise
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger("pywabot")
    logger.setLevel(log_level)


if __name__ == '__main__':
    setup_logging('debug')
    logging.debug("This is a debug message.")
    logging.info("This is an info message.")
    logging.warning("This is a warning message.")
    setup_logging('silent')
    logging.info("This message should not appear.")
