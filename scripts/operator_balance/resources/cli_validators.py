import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from .operator_accounts_model import OperatorAccountsModel


def parse_operators(file_path: str) -> list[OperatorAccountsModel]:
    with open(file_path) as f:
        data = json.load(f)
    operators = [OperatorAccountsModel(**operator) for operator in data]

    # remove duplicate accounts
    for operator in operators:
        operator.accounts = list(set(operator.accounts))

    return operators


def valid_url(url):
    try:
        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            return url
        else:
            raise argparse.ArgumentTypeError(f"'{url}' is not a valid URL.")
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{url}' is not a valid URL.")


def existing_dir(path_: str) -> Path:
    path = Path(path_)

    if not path.exists() or not path.is_dir():
        raise argparse.ArgumentTypeError(f"Directory {path} does not exist")

    return path
