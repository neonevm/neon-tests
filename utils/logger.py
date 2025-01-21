import logging


class Logger(logging.Logger):
    def setLevel(self, level):
        super().setLevel(level)

        for handler in self.handlers:
            handler.setLevel(level)


def create_logger(name: str, level: int = logging.INFO) -> Logger:
    logging.setLoggerClass(Logger)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    formatter = logging.Formatter("%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)")
    console_handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(console_handler)

    return logger
