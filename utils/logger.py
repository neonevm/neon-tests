import logging
import os
import re

from _pytest.logging import ColoredLevelFormatter
import allure

SECRET_ENV_VARS = [
    "DEVNET_FAUCET_URL",
    "DEVNET_SOLANA_URL",
]


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


def log_text_to_allure_and_stdout(title: str, message):
    logging.getLogger(__name__).info(f"{title}:\n{message}")
    allure.attach(message, name=title, attachment_type=allure.attachment_type.TEXT)


def redact_string(message: str, secret_env_var_names: list[str] | None = None) -> str:
    secret_env_var_names = secret_env_var_names or SECRET_ENV_VARS

    for secret_env_var_name in secret_env_var_names:
        value = os.getenv(secret_env_var_name)

        if value:
            pattern = re.escape(value.strip().removesuffix("/"))
            message = re.sub(pattern, f"<${secret_env_var_name}>", message)

    return message


class RedactingColoredLevelFormatter(ColoredLevelFormatter):
    def format(self, record: logging.LogRecord):
        unredacted = super().format(record)
        redacted = redact_string(unredacted)
        return redacted
