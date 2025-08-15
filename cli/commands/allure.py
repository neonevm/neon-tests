import click
import os
from pathlib import Path

from utils import cloud
from utils.consts import EnvName, TEST_GROUPS
from utils.types import TestGroup

ALLURE_REPORT_URL = "allure_report.url"


@click.group("allure")
@click.pass_context
def allure_cli(ctx):
    """Commands for load test manipulation."""


@allure_cli.command("upload-report", help="Upload allure history")
@click.argument("name", type=click.Choice(TEST_GROUPS))
@click.option("-n", "--network", default=EnvName.DEVNET, type=EnvName, help="In which stand run tests")
@click.option(
    "-s",
    "--source",
    default="./allure-report",
    type=click.Path(file_okay=False, dir_okay=True),
)
def upload_allure_report(name: TestGroup, network: EnvName, source: str = "./allure-report"):
    branch = os.environ.get("GITHUB_REF_NAME")
    build_id = os.environ.get("GITHUB_RUN_NUMBER")
    path = Path(name) / network.value / branch
    cloud.sync_allure_report_to_s3(source, path / build_id)

    report_url = f"http://neon-test-allure.s3-website.eu-central-1.amazonaws.com/{path / build_id}"

    with open(ALLURE_REPORT_URL, "w") as f:
        f.write(report_url)

    with open("/tmp/index.html", "w") as f:
        f.write(
            f"""<!DOCTYPE html><meta charset="utf-8"><meta http-equiv="refresh" content="0; URL={report_url}">
        <meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">
        """
        )

    cloud.upload("/tmp/index.html", path)
    print(f"Allure report link: {report_url}")

    with open("allure_report_info", "w") as f:
        f.write(f"🔗 Allure [report]({report_url})\n")
