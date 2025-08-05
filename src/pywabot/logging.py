import logging
import sys

def setup_logging(level='info'):
    
    if level.lower() == 'silent':
        logging.disable(logging.CRITICAL)
        return

    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True
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
