import logging.config
import os
import yaml
from dotenv import load_dotenv

load_dotenv()

LOGGER_CFG = os.environ["LOGGER_CFG"]


def init_logger(logger_module_name):
    with open(LOGGER_CFG, 'r') as f:
        log_cfg = yaml.safe_load(f.read())

    logging.config.dictConfig(log_cfg)
    return logging.getLogger(logger_module_name)


