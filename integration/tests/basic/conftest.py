import json
import pathlib


def pytest_collection_modifyitems(config, items):
    deselected_items = []
    selected_items = []
    deselected_marks = []
    network_name = config.getoption("--network")

    if "devnet" in network_name:
        deselected_marks.append("only_stands")
    else:
        deselected_marks.append("only_devnet")

    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)

    if len(environments[network_name]["network_ids"]) == 1:
        deselected_marks.append("multipletokens")

    for item in items:
        if any([item.get_closest_marker(mark) for mark in deselected_marks]):
            deselected_items.append(item)
        else:
            selected_items.append(item)

    config.hook.pytest_deselected(items=deselected_items)
    items[:] = selected_items
