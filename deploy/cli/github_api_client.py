import os
import re
import typing as tp
from pathlib import Path

import click
import requests

from utils.types import GithubEvent, RepoType

DAPPS_REPORT_COMMENT_TITLE = "<summary>Dapps report</summary>"


class GithubClient:
    def __init__(
            self,
            token: str,
            repo: tp.Union[RepoType, tp.Literal[""]] = "",
            event_name: str = "",
            ref: str = "",
            ref_name: str = "",
            head_ref: str = "",
            base_ref: str = "",
            last_commit_message: str = "",
    ):
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        self.repo = repo
        self.event_name = event_name
        self.ref = ref
        self.ref_name = ref_name
        self.head_ref = head_ref
        self.base_ref = base_ref
        self.last_commit_message = last_commit_message

    def add_comment_to_pr(self, url: str, msg: str):
        data = {"body": f"<details>{DAPPS_REPORT_COMMENT_TITLE}\n\n{msg}\n\n"}
        click.echo(f"Sent data: {data}")
        click.echo(f"Headers: {self.headers}")
        response = requests.post(url, json=data, headers=self.headers)
        click.echo(f"Status code: {response.status_code}")
        if response.status_code != 201:
            raise RuntimeError(f"Attempt to leave a comment on a PR failed: {response.text}")

    def delete_last_comment(self, pr_url: str):
        response = requests.get(pr_url, headers=self.headers).json()
        old_comment_id = None
        for item in response:
            if DAPPS_REPORT_COMMENT_TITLE in item["body"]:
                old_comment_id = item["id"]
                break
        if old_comment_id:
            pattern = r"/(\d+)/comments"
            repo_url = re.sub(pattern, "", pr_url)
            comment_url = f"{repo_url}/comments/{old_comment_id}"
            response = requests.delete(comment_url, headers=self.headers)
            if response.status_code != 204:
                print(f"Attempt to delete a comment on a PR failed: {response.text}")

    @property
    def event(self) -> GithubEvent:
        if "merge" in self.last_commit_message.lower():
            return "merge_request"
        if self.event_name == 'push':
            if self.ref.startswith('refs/tags/'):
                return "push_with_tag"
            elif self.ref.startswith('refs/heads/'):
                return "push_no_tag"
            else:
                return "unknown"
        elif self.event_name == 'pull_request':
            return "pull_request"
        elif self.event_name == 'workflow_dispatch':
            return "workflow_dispatch"
        else:
            return "unknown"

    @property
    def base_branch(self) -> tp.Optional[str]:
        if any(substring in self.event for substring in ("pull", "push")):
            if "refs" in self.base_ref:
                return self.base_ref[len('refs/heads/'):]
            else:
                return self.base_ref

    @property
    def tag_name(self) -> tp.Optional[str]:
        if self.event == "push_with_tag":
            return self.ref_name

    @property
    def source_and_target_branch_names(self) -> tp.Optional[tuple[str, str]]:
        if self.event == "pull_request":
            return self.head_ref, self.base_ref
        return None

    def is_feature_branch(self, branch: str) -> bool:
        is_base = self.is_base_branch(branch)
        is_version = self.is_version_branch(branch)
        return not is_base and not is_version

    @staticmethod
    def is_base_branch(branch: str) -> bool:
        pattern = re.compile(r"^(main|master|develop)$")
        is_base = True if pattern.match(branch) else False
        return is_base

    @staticmethod
    def is_version_branch(branch: str) -> bool:
        from clickfile import VERSION_BRANCH_TEMPLATE
        is_base = True if re.fullmatch(VERSION_BRANCH_TEMPLATE, branch) else False
        return is_base

    def upload_artifact(self, path: str) -> str:
        artifact_name = Path(path).stem
        file_size = os.path.getsize(path)

        with open(path, 'rb') as file:
            upload_url = self.__create_artifact_upload_url(artifact_name=artifact_name, size=file_size)
            response = requests.put(upload_url, headers=self.headers, data=file)
        response.raise_for_status()

        artifact_url = self.__get_artifact_url(artifact_name=artifact_name)
        return artifact_url

    @staticmethod
    def get_artifacts_url() -> str:
        owner = os.environ['GITHUB_REPOSITORY_OWNER']
        repo = os.environ['GITHUB_REPOSITORY_NAME']
        workflow_run_id = os.environ['GITHUB_RUN_ID']
        url = f'https://api.github.com/repos/{owner}/{repo}/actions/runs/{workflow_run_id}/artifacts'
        return url

    def __create_artifact_upload_url(self, artifact_name: str, size: int) -> str:
        url = self.get_artifacts_url()
        response = requests.post(url, headers=self.headers, json={
            'name': artifact_name,
            'size': size
        })
        response.raise_for_status()
        return response.json()['upload_url']

    def __get_artifact_url(self, artifact_name: str) -> str:
        url = self.get_artifacts_url()
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        artifacts = response.json()['artifacts']

        for artifact in artifacts:
            if artifact['name'] == artifact_name:
                return artifact['archive_download_url']

        raise Exception(f'Artifact {artifact_name} not found')
