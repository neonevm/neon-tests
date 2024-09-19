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

    # Disable Request Manager, as it only shows duplication information regarding method names,
    # which HTTPProvider already does
    logging.getLogger("web3.RequestManager").setLevel(logging.WARNING)

    # Disable all internal debug logging of requests and urllib3
    # E.g. HTTP traffic
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger


def time_measure(start_time, end_time, job_name=""):
    elapsed_time = end_time - start_time
    elapsed_minutes = elapsed_time / 60
    log_message = f"Job {job_name}, Time: {elapsed_time:.2f}s"

    if elapsed_minutes > 15:
        log_message += " (15m+)"
    elif elapsed_minutes > 10:
        log_message += " (10m+)"
    elif elapsed_minutes > 5:
        log_message += " (5m+)"

    return log_message
