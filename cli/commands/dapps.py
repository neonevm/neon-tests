#!/usr/bin/env python3
import typing as tp

from deploy.cli import cost_report
from deploy.cli.github_api_client import GithubClient
from utils.types import RepoType
import click

VERSION_BRANCH_TEMPLATE = r"[vt]{1}\d{1,2}\.\d{1,2}\.x.*"


@click.group("dapps", help="Manage dapps")
def dapps():
    pass


@dapps.command("save_dapps_cost_report_to_db", help="Save dApps Cost Report to db")
@click.option("-d", "--directory", default="reports", help="Directory with reports")
@click.option("--repo", type=click.Choice(tp.get_args(RepoType)), required=True)
@click.option("--evm_tag", required=True)
@click.option("--proxy_tag", required=True)
@click.option("--evm_commit_sha", required=True)
@click.option("--proxy_commit_sha", required=True)
def save_dapps_cost_report_to_db(
    directory: str,
    repo: RepoType,
    evm_tag: str,
    proxy_tag: str,
    evm_commit_sha: str,
    proxy_commit_sha: str,
):
    cost_report.save_dapps_cost_report_to_db(
        directory=directory,
        repo=repo,
        evm_tag=evm_tag,
        proxy_tag=proxy_tag,
        evm_commit_sha=evm_commit_sha,
        proxy_commit_sha=proxy_commit_sha,
        version_branch_template=VERSION_BRANCH_TEMPLATE,
    )


@dapps.command("save_dapps_cost_report_to_md", help="Save dApps Cost Report to cost_reports.md")
@click.option("-d", "--directory", default="reports", help="Directory with reports")
def save_dapps_cost_report_to_md(directory: str):
    cost_report.save_dapps_cost_report_to_md(directory=directory)


@dapps.command("compare_dapp_cost_reports", help="Compare dApp results")
@click.option("--repo", type=click.Choice(tp.get_args(RepoType)), required=True)
@click.option("--evm_tag", required=True)
@click.option("--proxy_tag", required=True)
@click.option("--version_branch", required=True)
@click.option("--history_depth_limit", type=int, help="How many runs to include into statistical analysis")
def compare_dapp_results(
    repo: RepoType,
    evm_tag: str,
    proxy_tag: str,
    version_branch: str,
    history_depth_limit: int,
):
    cost_report.compare_dapp_results(
        repo=repo,
        evm_tag=evm_tag,
        proxy_tag=proxy_tag,
        version_branch=version_branch,
        history_depth_limit=history_depth_limit,
    )


@dapps.command("validate_cost_reports", help="Validate cost reports data")
@click.option("--repo", type=click.Choice(tp.get_args(RepoType)), required=True)
@click.option("--evm_tag", required=True)
@click.option("--proxy_tag", required=True)
@click.option("--version_branch", required=True)
@click.option("--acc_count", type=int, help="Allowed acc_count increase")
@click.option("--trx_count", type=int, help="Allowed trx_count increase")
@click.option("--gas_estimated", type=int, help="Allowed gas_estimated increase")
@click.option("--gas_used", type=int, help="Allowed gas_used increase")
@click.option("--compute_units", type=int, help="Allowed compute_units increase")
@click.option("--output", type=str, help="Path to the JSON file where detected failures are saved")
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
    cost_report.validate_cost_reports(
        repo=repo,
        evm_tag=evm_tag,
        proxy_tag=proxy_tag,
        version_branch=version_branch,
        acc_count=acc_count,
        trx_count=trx_count,
        gas_estimated=gas_estimated,
        gas_used=gas_used,
        compute_units=compute_units,
        output=output,
    )


@dapps.command("add_pr_comment", help="Add PR comment with dApp cost reports")
@click.option("--pr_url_for_report", default="", help="Url to send the report as comment for PR")
@click.option("--token", default="", help="github token")
@click.option("--md_file", help="File with markdown for the comment")
@click.option("--title", default="", help="Comment title")
def add_pr_comment(pr_url_for_report: str, token: str, md_file: str, title: str):
    gh_client = GithubClient(token=token)
    gh_client.delete_last_comment(pr_url=pr_url_for_report, title=title)

    with open(md_file) as f:
        markdown = f.read()

    gh_client.add_comment_to_pr(url=pr_url_for_report, msg=markdown, title=title)
