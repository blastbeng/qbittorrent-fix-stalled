# -*- coding:utf-8 -*-
# Logging System

import os
import logging
from datetime import datetime

class Logger(object):
    # Logger Settings
    LOG_FILE_NAME = 'autoremove.%s.log'
    OUTPUT_FORMAT = '%(asctime)s %(name)s %(levelname)s: %(message)s'
    DATE_FORMAT = '%a, %d %b %Y %H:%M:%S'

    # Log Console Handler; Use StreamHandler to output to screen
    console_handler = None

    @staticmethod
    def init(log_path = '', file_debug_log = False, output_debug_log = False):

        # Initialize the console handler
        Logger.console_handler = logging.StreamHandler()
        Logger.console_handler.setLevel(int(os.environ.get("LOG_LEVEL")))
        console_handler_formatter = logging.Formatter(Logger.OUTPUT_FORMAT, datefmt=Logger.DATE_FORMAT)
        Logger.console_handler.setFormatter(console_handler_formatter)

    @staticmethod
    def register(name):
        logger = logging.getLogger(name)

        # Remove old loggers
        logger.handlers = []

        # Configure logging
        logger.setLevel(int(os.environ.get("LOG_LEVEL")))

        # Add Handlers
        logger.addHandler(Logger.console_handler)

        return logger