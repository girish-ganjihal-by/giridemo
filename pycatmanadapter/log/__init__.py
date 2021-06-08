import logging
import sys

# finalize format later (Splunk friendly)
log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

logger = logging.getLogger()

# log level should be configurable
logger.setLevel(logging.DEBUG)

# for now, log to stdout
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)
