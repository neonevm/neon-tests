import json
import pathlib

from clickfile import network_manager
from utils import web3client
from packaging import version


def pytest_collection_modifyitems(config, items):
    deselected_items = []
    selected_items = []
    deselected_marks = []
    network_name = config.getoption("--network")

    if network_name == "geth":
        return

    settings = network_manager.get_network_object(network_name)
    web3_client = web3client.NeonChainWeb3Client(settings["proxy_url"])

    raw_proxy_version = web3_client.get_proxy_version()["result"]

    if "Neon-proxy/" in raw_proxy_version:
        raw_proxy_version = raw_proxy_version.split("Neon-proxy/")[1].strip()
    proxy_dev = "dev" in raw_proxy_version

    if "-" in raw_proxy_version:
        raw_proxy_version = raw_proxy_version.split("-")[0].strip()
    proxy_version = version.parse(raw_proxy_version)

    if network_name == "devnet":
        deselected_marks.append("only_stands")
    else:
        deselected_marks.append("only_devnet")

    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)

    if len(environments[network_name]["network_ids"]) == 1:
        deselected_marks.append("multipletokens")

    for item in items:
        raw_item_pv = [mark.args[0] for mark in item.iter_markers(name="proxy_version")]
        select_item = True

        if any([item.get_closest_marker(mark) for mark in deselected_marks]):
            deselected_items.append(item)
            select_item = False
        elif len(raw_item_pv) > 0:
            item_proxy_version = version.parse(raw_item_pv[0])

            if not proxy_dev and item_proxy_version > proxy_version:
                deselected_items.append(item)
                select_item = False

        if select_item:
            selected_items.append(item)

    config.hook.pytest_deselected(items=deselected_items)
    items[:] = selected_items
