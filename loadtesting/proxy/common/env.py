import json
import logging
import pathlib
from dataclasses import dataclass

from locust import events


LOG = logging.getLogger(__name__)


@dataclass
class NeonGlobalEnv:
    accounts = []
    counter_contracts = []
    erc20_contracts = {}
    erc20_wrapper_contracts = {}
    increase_storage_contracts = []


@events.init_command_line_parser.add_listener
def arg_parser(parser):
    """Add custom command line arguments to Locust"""
    parser.add_argument(
        "--credentials",
        type=str,
        env_var="NEON_CRED",
        default="envs.json",
        help="Relative path to environment credentials file.",
    )


@events.test_start.add_listener
def make_env_preparation(environment, **kwargs):
    neon = NeonGlobalEnv()
    environment.shared = neon


@events.test_start.add_listener
def load_credentials(environment, **kwargs):
    """Test start event handler"""
    base_path = pathlib.Path().absolute()
    path = base_path / environment.parsed_options.credentials
    network = environment.parsed_options.host or environment.host
    if not (path.exists() and path.is_file()):
        path = base_path / "envs.json"
    with open(path, "r") as fp:
        f = json.load(fp)
        environment.credentials = f[network]
