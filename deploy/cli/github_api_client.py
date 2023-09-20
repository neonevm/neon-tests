import click
import requests


class GithubClient:

    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json"}

    def add_comment_to_pr(self, url, msg):
        data = {"body": f"```{msg}```"}
        response = requests.post(url, json=data, headers=self.headers)
        click.echo(f"Sent data: {data}")
        click.echo(f"Headers: {self.headers}")
        click.echo(f"Status code: {response.status_code}")
        if response.status_code != 204:
            raise RuntimeError(f"Attempt to leave a comment on a PR failed: {response.text}")
