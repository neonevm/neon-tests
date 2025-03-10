import re

import click
import requests

COMMENT_TITLE = "<summary>{title}</summary>"


class GithubClient:
    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

    def add_comment_to_pr(self, url, msg, title: str):
        data = {"body": f"<details>{COMMENT_TITLE.format(title=title)}\n\n{msg}\n\n"}
        click.echo(f"Sent data: {data}")
        click.echo(f"Headers: {self.headers}")
        response = requests.post(url, json=data, headers=self.headers)
        click.echo(f"Status code: {response.status_code}")
        if response.status_code != 201:
            raise RuntimeError(f"Attempt to leave a comment on a PR failed: {response.text}")

    def delete_last_comment(self, pr_url, title: str):
        response = requests.get(pr_url, headers=self.headers).json()
        old_comment_id = None
        for item in response:
            if COMMENT_TITLE.format(title=title) in item["body"]:
                old_comment_id = item["id"]
                break
        if old_comment_id:
            pattern = r"/(\d+)/comments"
            repo_url = re.sub(pattern, "", pr_url)
            comment_url = f"{repo_url}/comments/{old_comment_id}"
            response = requests.delete(comment_url, headers=self.headers)
            if response.status_code != 204:
                print(f"Attempt to delete a comment on a PR failed: {response.text}")
