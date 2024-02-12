import logging

import allure


class AllureLogger(logging.Handler):
    def emit(self, record):
        if logging.DEBUG < record.levelno:
            with allure.step(f"LOG ({record.levelname}): {record.getMessage()}"):
                pass
