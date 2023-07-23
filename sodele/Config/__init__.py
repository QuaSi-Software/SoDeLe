import logging as python_logging
import os
import sys
from functools import cache

from sodele.Helper import runsInDocker, getValueForKey, strToBool


class BaseConfig:
    STACK_TRACE = True
    DEBUG = True


class DockerConfig(BaseConfig):
    STACK_TRACE = False


class ProductionConfig(DockerConfig):
    DEBUG = False


def getConfig():
    config = BaseConfig
    # check if running in docker
    if runsInDocker():
        config = DockerConfig
        # check if "--production" is in the command line arguments
        if "--production" in sys.argv:
            config = ProductionConfig
    return config


@cache
def logging():
    """
    This Function returns a logger for the application.

    :return:    A Logger
    """

    logging_lookup = {
        "DEBUG": python_logging.DEBUG,
        "INFO": python_logging.INFO,
        "WARNING": python_logging.WARNING,
        "ERROR": python_logging.ERROR,
        "CRITICAL": python_logging.CRITICAL,
    }
    # get the logger
    logger = python_logging.getLogger("SODELE")
    # get env variable for logging level
    log_level = getValueForKey("SODELE_LOG_LEVEL", "INFO")
    # set the logging level
    logger.setLevel(logging_lookup[log_level])
    # format to use the Current time
    formatter = python_logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # check via env if the logging should be printed to the console
    logToConsole = strToBool(getValueForKey("SODELE_LOG_TO_CONSOLE", "True"))
    if logToConsole:
        # create a console handler
        ch = python_logging.StreamHandler()
        ch.setLevel(logging_lookup[log_level])
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    else:
        # create a file handler
        fh = python_logging.FileHandler(f"./var/log/rudi.log")
        fh.setLevel(logging_lookup[log_level])
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    return logger
