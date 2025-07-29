import glob
import json
import os
import pathlib
import re
from collections import Counter
from typing import TypedDict, Literal

import click
import pandas as pd
from solana.rpc.commitment import Confirmed
from solana.transaction import Signature

from deploy.cli.network_manager import NetworkManager
from deploy.test_results_db.db_handler import PostgresTestResultsHandler
from deploy.test_results_db.test_results_handler import TestResultsHandler
from utils.solana_client import SolanaClient
from utils.types import RepoType
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


def get_service_tags_for_cost_reports(
    evm_tag: str,
    proxy_tag: str,
    repo: RepoType,
    db: PostgresTestResultsHandler,
    limit: int,
    version_branch: str,
) -> tuple[str, str, list[str], Literal["timestamp", "branch_name"]]:
    """
    :param evm_tag:
    :param proxy_tag:
    :param repo:
    :param db:
    :param limit: number of previous tags. E.g. if you want to compare 5 reports - you need 4 previous tags
    :param version_branch:
    :return:
    """
    from clickfile import GITHUB_TAG_PATTERN

    compared_service_tag = evm_tag if repo == "evm" else proxy_tag
    other_service_tag = evm_tag if repo == "proxy" else proxy_tag

    # define the tags against which the comparison will be done
    previous_tags: list[str]
    order_by: Literal["timestamp", "branch_name"]

    if re.fullmatch(GITHUB_TAG_PATTERN, compared_service_tag):
        previous_tags = db.get_previous_tags(
            repo=repo,
            tag=compared_service_tag,
            limit=limit,
        )
        order_by = "branch_name"
    else:
        if version_branch:
            previous_tags = [version_branch]
        else:
            previous_tags = ["latest"]
        order_by = "timestamp"
    click.echo(f"order_by: {order_by}")
    return compared_service_tag, other_service_tag, previous_tags, order_by


def save_dapps_cost_report_to_db(
    directory: str,
    repo: RepoType,
    evm_tag: str,
    proxy_tag: str,
    evm_commit_sha: str,
    proxy_commit_sha: str,
    version_branch_template: str,
):
    tag = evm_tag if repo == "evm" else proxy_tag

    report_data = prepare_report_data(directory)
    db = PostgresTestResultsHandler()

    # define if previous similar reports should be deleted
    is_neon_evm_tag_version_branch = bool(re.fullmatch(version_branch_template, evm_tag))
    is_proxy_tag_version_branch = bool(re.fullmatch(version_branch_template, proxy_tag))

    if evm_tag == proxy_tag == "latest":
        click.echo("This is a merge to develop")
        do_delete = False
    elif is_neon_evm_tag_version_branch and is_proxy_tag_version_branch and evm_tag == proxy_tag:
        click.echo(f"This is a merge to version branch {evm_tag}")
        do_delete = False
    else:
        do_delete = True

    # delete them if needed
    if do_delete:
        report_ids_old = db.get_cost_report_ids(repo=repo, tag=tag)
        if report_ids_old:
            db.delete_data_by_report_ids(report_ids=report_ids_old)
            db.delete_reports(report_ids=report_ids_old)

    # save the new report
    report_id_new = db.save_cost_report(
        repo=repo,
        neon_evm_tag=evm_tag,
        proxy_tag=proxy_tag,
        evm_commit_sha=evm_commit_sha,
        proxy_commit_sha=proxy_commit_sha,
    )
    db.save_cost_report_data(report_data=report_data, cost_report_id=report_id_new)


def save_dapps_cost_report_to_md(directory: str):
    report_data = prepare_report_data(directory)

    # Add 'gas_used_%' column after 'gas_used'
    report_data.insert(
        report_data.columns.get_loc("gas_used") + 1,
        "gas_used_%",
        (report_data["gas_used"] / report_data["gas_estimated"]) * 100,
    )
    report_data["gas_used_%"] = report_data["gas_used_%"].round(2)

    # Dump report_data DataFrame to markdown, grouped by the dApp
    report_as_markdown_table = report_data_to_markdown(df=report_data)
    pathlib.Path("cost_reports.md").write_text(report_as_markdown_table)


def compare_dapp_results(
    repo: RepoType,
    evm_tag: str,
    proxy_tag: str,
    version_branch: str,
    history_depth_limit: int,
):
    click.echo(f"compare_dapp_results: {locals()}")
    db = PostgresTestResultsHandler()
    compared_service_tag, other_service_tag, previous_tags, order_by = get_service_tags_for_cost_reports(
        evm_tag=evm_tag,
        proxy_tag=proxy_tag,
        repo=repo,
        db=db,
        limit=history_depth_limit - 1,
        version_branch=version_branch,
    )
    click.echo(f"previous_tags: {previous_tags}")

    historical_data = db.get_historical_data(
        depth=history_depth_limit,
        repo=repo,
        latest_tag=compared_service_tag,
        previous_tags=previous_tags,
        order_by=order_by,
    )

    # get commit sha for compared_service and other_service
    data_sample_row = historical_data[
        (historical_data["repo"] == repo)
        & (historical_data["neon_evm_tag"] == evm_tag)
        & (historical_data["proxy_tag"] == proxy_tag)
    ].iloc[0]

    if repo == "evm":
        compared_service_commit_sha = data_sample_row["evm_commit_sha"]
        other_service_commit_sha = data_sample_row["proxy_commit_sha"]
    elif repo == "proxy":
        compared_service_commit_sha = data_sample_row["proxy_commit_sha"]
        other_service_commit_sha = data_sample_row["evm_commit_sha"]
    else:
        raise ValueError(f'Unknown repo "{repo}"')

    compared_service_sha_string = f", commit sha {compared_service_commit_sha}" if compared_service_commit_sha else ""
    other_service_sha_string = f", commit sha {other_service_commit_sha}" if other_service_commit_sha else ""

    # generate plots and save to pdf
    other_service_name = "neon_evm" if repo == "proxy" else "proxy"
    test_results_handler = TestResultsHandler()
    test_results_handler.generate_and_save_plots_pdf(
        historical_data=historical_data,
        title_end=f"on {repo}:{compared_service_tag}{compared_service_sha_string}\n"
        f"with {other_service_name}:{other_service_tag}{other_service_sha_string}",
        output_pdf="cost_reports.pdf",
    )


def validate_cost_reports(
    repo: RepoType,
    evm_tag: str,
    proxy_tag: str,
    version_branch: str,
    acc_count: int,
    trx_count: int,
    gas_estimated: int,
    gas_used: int,
    compute_units: int,
    output: str,
):
    """
    Compares the cost report data for <repo>:<evm_tag|proxy_tag|version_branch>
    with previous report data based on acceptable increases in metrics.
    Any detected increases exceeding the allowed thresholds are saved to the <output> file.

    :param repo: Repository name.
    :param evm_tag: EVM tag of the report data.
    :param proxy_tag: Proxy tag of the report data.
    :param version_branch: Version branch.
    :param acc_count: Maximum acceptable increase in acc_count.
    :param trx_count: Maximum acceptable increase in trx_count.
    :param gas_estimated: Maximum acceptable increase in gas_estimated.
    :param gas_used: Maximum acceptable increase in gas_used.
    :param compute_units: Maximum acceptable increase in compute_units.
    :param output: Path to the JSON file where detected failures are saved.
    """
    db = PostgresTestResultsHandler()
    compared_service_tag, other_service_tag, previous_tags, order_by = get_service_tags_for_cost_reports(
        evm_tag=evm_tag,
        proxy_tag=proxy_tag,
        repo=repo,
        db=db,
        limit=1,
        version_branch=version_branch,
    )
    click.echo(f"previous_tags: {previous_tags}")

    historical_data = db.get_historical_data(
        depth=2,
        repo=repo,
        latest_tag=compared_service_tag,
        previous_tags=previous_tags,
        order_by=order_by,
    )

    all_metric_names = "acc_count", "trx_count", "gas_estimated", "gas_used", "compute_units"
    dapp_names = historical_data["dapp_name"].unique()

    failure = TypedDict("failure", {"dapp": str, "action": str, "metric": str, "INCREASE": int})
    failures: list[failure] = []

    for dapp_name in dapp_names:
        data_for_dapp = historical_data[historical_data["dapp_name"] == dapp_name]
        actions = data_for_dapp["action"].unique()

        for action in actions:
            data_for_dapp_action = data_for_dapp[data_for_dapp["action"] == action]
            metric_names = [col_name for col_name in data_for_dapp_action.columns if col_name in all_metric_names]

            for metric_name in metric_names:
                metric_values = data_for_dapp_action[metric_name]
                historical_value = metric_values.iloc[0]
                latest_value = metric_values.iloc[-1]

                if not pd.isna(historical_value) and not pd.isna(latest_value):
                    actual_change = latest_value - historical_value
                    max_acceptable_change = locals()[metric_name]

                    if actual_change > max_acceptable_change:
                        failure_dict: failure = {
                            "dapp": dapp_name,
                            "action": action,
                            "metric": metric_name,
                            "INCREASE": actual_change,
                        }
                        failures.append(failure_dict)

    if failures:
        df = pd.DataFrame(failures)
        md = df.to_markdown(output, index=False)


def get_solana_accounts_transactions_compute_units(eth_transaction):
    print("**********************************************************************")
    print(f"Neon transaction {eth_transaction}")
    network = os.environ.get("NETWORK")
    network_manager = NetworkManager(network)
    solana_url = network_manager.get_network_param(network, "solana_url")
    proxy_url = network_manager.get_network_param(network, "proxy_url")
    sol_client = SolanaClient(solana_url)
    web3_client = NeonChainWeb3Client(proxy_url)
    trx = web3_client.get_solana_trx_by_neon(eth_transaction)
    print(f"neon_getSolanaTransactionByNeonTransaction(eth_transaction={eth_transaction}): {trx}")
    print(f"minimum_ledger_slot={sol_client.get_minimum_ledger_slot()}")
    print(f"first_available_block={sol_client.get_first_available_block()}")
    print(f"get_slot={sol_client.get_slot()}")
    tr = sol_client.get_transaction(
        Signature.from_string(trx["result"][0]), max_supported_transaction_version=0, commitment=Confirmed
    )
    print(f"get_transaction({trx}): {tr}")

    solana_transaction_hashes = trx["result"]
    print(f"trx_count ({len(solana_transaction_hashes)}): {solana_transaction_hashes}")
    compute_units = 0

    for solana_transaction_hash in solana_transaction_hashes:
        solana_transaction = sol_client.get_transaction(
            tx_sig=Signature.from_string(solana_transaction_hash),
            max_supported_transaction_version=0,
            commitment=Confirmed,
        )
        compute_units_consumed = int(solana_transaction.value.transaction.meta.compute_units_consumed)
        compute_units += compute_units_consumed
        print(f"Compute units {solana_transaction_hash}: {compute_units_consumed}")

    if tr.value.transaction.transaction.message.address_table_lookups:
        alt = tr.value.transaction.transaction.message.address_table_lookups
        print(f"Atl: {alt}")
        return len(alt[0].writable_indexes) + len(alt[0].readonly_indexes), len(trx["result"]), compute_units
    else:
        account_keys = tr.value.transaction.transaction.message.account_keys
        print(f"Account keys ({len(account_keys)}): {account_keys}")
        return len(tr.value.transaction.transaction.message.account_keys), len(trx["result"]), compute_units
