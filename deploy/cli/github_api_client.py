import re

import click
import requests

DAPPS_REPORT_COMMENT_TITLE = "<summary>Dapps report</summary>"


class GithubClient:

    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json"}

    def add_comment_to_pr(self, url, msg):
        data = {"body": f"<details>{DAPPS_REPORT_COMMENT_TITLE}\n```\n{msg}\n```\n</details>"}
        click.echo(f"Sent data: {data}")
        click.echo(f"Headers: {self.headers}")
        response = requests.post(url, json=data, headers=self.headers)
        click.echo(f"Status code: {response.status_code}")
        if response.status_code != 201:
            raise RuntimeError(f"Attempt to leave a comment on a PR failed: {response.text}")

    def delete_last_comment(self, pr_url):
        response = requests.get(pr_url, headers=self.headers).json()
        old_comment_id = None
        for item in response:
            if DAPPS_REPORT_COMMENT_TITLE in item["body"]:
                old_comment_id=item["id"]
                break
        if old_comment_id:
            pattern = r'/(\d+)/comments'
            repo_url = re.sub(pattern, '', pr_url)
            comment_url = f'{repo_url}/comments/{old_comment_id}'
            response = requests.delete(comment_url, headers=self.headers)
            if response.status_code != 204:
                print(f"Attempt to delete a comment on a PR failed: {response.text}")


