#!/usr/bin/env python3
from collections import defaultdict
from urllib.parse import urlparse

import click
import requests

from utils.consts import EnvName
from utils.error_log import error_log
from utils.slack_notification import SlackNotification
from utils.types import TestGroup


@click.command(help="Send notification to slack")
@click.option("-u", "--url", help="slack app endpoint url.")
@click.option("-b", "--build_url", help="github action test build url.")
@click.option(
    "-n", "--network", type=click.Choice(EnvName), default=EnvName.DEVNET.value, help="In which stand run tests"
)
@click.option("--test-group", help="Name of the failed test group")
@click.option("--report-url", multiple=True, help="Urls to Allure report")
@click.option("--report-group", multiple=True, help="Test group of Allure report")
def send_notification(url, build_url, network, test_group: str, report_url: tuple[str], report_group: tuple[str]):
    slack_notification = SlackNotification()

    # build info
    parsed_build_url = urlparse(build_url).path.split("/")
    build_id = parsed_build_url[-1]
    build_info = {"id": build_id, "url": build_url}

    # failed tests group or count if available
    failed_count_by_group: defaultdict[TestGroup, int] = error_log.get_count_by_group()
    if failed_count_by_group:
        failed_tests = "\n".join(f"{group}: {count}" for group, count in failed_count_by_group.items())
    else:
        failed_tests = test_group

    # Allure report urls
    report_urls = []

    for i, report_url_ in enumerate(report_url):
        if report_url_:
            report_urls.append({"name": report_group[i], "url": report_url_})

    # add combined block
    slack_notification.add_combined_block(
        build_info=build_info,
        network=network,
        failed_tests=failed_tests,
        report_urls=report_urls,
        comments=error_log.read().comments,
    )

    # add the divider
    slack_notification.add_divider()

    # send the notification
    payload = slack_notification.model_dump_json()
    response = requests.post(url=url, data=payload)
    if response.status_code != 200:
        click.echo(f"Response status code: {response.status_code}")
        click.echo(f"Response text: {response.text}")
        click.echo(f"Payload: {payload}")
        raise RuntimeError("Notification is not sent")
