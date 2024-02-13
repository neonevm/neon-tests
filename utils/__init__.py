import logging
import typing as tp
import pathlib


def create_allure_environment_opts(opts: dict, dst: tp.Optional[pathlib.Path] = None):
    if dst is None:
        dst = pathlib.Path() / "allure-results" / "environment.properties"
    with open(dst, "a+") as file:
        file.write(
            "\n".join(
                map(
                    lambda x: f"{x[0]}={x[1] if x[1] and len(x[1]) > 0 else 'empty value'}",
                    opts.items(),
                )
            )
        )
        file.write("\n")


def setup_logging(log_level=logging.DEBUG):
    """Setup root logger and quiet some levels."""
    logger = logging.getLogger()
    logger.setLevel(log_level)

    logging.getLogger("web3.RequestManager").setLevel(logging.WARNING)

    # Disable all internal debug logging of requests and urllib3
    # E.g. HTTP traffic
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger
