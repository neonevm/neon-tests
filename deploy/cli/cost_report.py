import glob
import json
import os
import pathlib
import re
from collections import Counter

import pandas as pd

from deploy.cli.infrastructure import get_solana_accounts_transactions_compute_units
from deploy.cli.network_manager import NetworkManager
from utils.web3client import NeonChainWeb3Client


def prepare_report_data(directory: str) -> pd.DataFrame:
    network_manager = NetworkManager(os.environ.get("NETWORK"))
    proxy_url = network_manager.get_network_param(os.environ.get("NETWORK"), "proxy_url")
    web3_client = NeonChainWeb3Client(proxy_url)

    reports = {}
    for path in glob.glob(str(pathlib.Path(directory) / "*-report.json")):
        with open(path, "r") as f:
            rep = json.load(f)
            if isinstance(rep, list):
                for r in rep:
                    if "actions" in r:
                        reports[r["name"]] = r["actions"]
            else:
                if "actions" in rep:
                    reports[rep["name"]] = rep["actions"]

    data = []

    for app, actions in reports.items():
        counts = Counter([action["name"].lower().strip() for action in actions])
        duplicate_actions = [action for action, count in counts.items() if count > 1]
        added_numbers = {dup_action: 1 for dup_action in duplicate_actions}

        for action in actions:
            # Ensure action name is unique by appending a counter if necessary
            base_action_name = action["name"].lower().strip()
            if base_action_name in duplicate_actions:
                added_number = added_numbers[base_action_name]
                unique_action_name = f"{base_action_name} {added_number}"
                added_numbers[base_action_name] += 1
            else:
                unique_action_name = base_action_name

            accounts, trx, compute_units = get_solana_accounts_transactions_compute_units(action["tx"])
            # accounts, trx, compute_units = (2, 12, 8946)
            tx = web3_client.get_transaction_by_hash(action["tx"])
            estimated_gas = int(tx.gas) if tx and tx.gas else None
            # estimated_gas = 122879
            used_gas = int(action["usedGas"])

            data.append(
                {
                    "dapp_name": app.lower().strip(),
                    "action": unique_action_name,
                    "acc_count": accounts,
                    "trx_count": trx,
                    "gas_estimated": estimated_gas,
                    "gas_used": used_gas,
                    "compute_units": compute_units,
                }
            )

    df = pd.DataFrame(data)
    if df.empty:
        raise Exception(f"no reports found in {directory}")
    return df


def report_data_to_markdown(df: pd.DataFrame) -> str:
    report_content = ""
    dapp_names = df["dapp_name"].unique()
    df.columns = [col.upper() for col in df.columns]
    df["GAS_USED_%"] = df["GAS_USED_%"].apply(lambda x: f"{x:.2f}")

    for dapp_name in dapp_names:
        dapp_df = df[df["DAPP_NAME"] == dapp_name].drop(columns="DAPP_NAME")

        # sort by ACTION (to mitigate [action 1, action 10, action 2, ...])
        dapp_df[["ACTION_TEXT", "ACTION_NUM"]] = dapp_df["ACTION"].apply(split_action).apply(pd.Series)
        dapp_df = dapp_df.sort_values(by=["ACTION_TEXT", "ACTION_NUM"])
        dapp_df = dapp_df.drop(columns=["ACTION_TEXT", "ACTION_NUM"])

        report_content += f'\n## Cost Report for "{dapp_name.title()}" dApp\n\n'
        report_content += dapp_df.to_markdown(index=False) + "\n"

    return report_content


def split_action(action) -> tuple[str, int]:
    match = re.match(r"(.+?)\s*(\d*)$", action)
    text_ = match.group(1)
    number = int(match.group(2)) if match.group(2).isdigit() else 0
    return text_, number
